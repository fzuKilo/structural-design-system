# -*- coding: utf-8 -*-
"""E2 baselines B1 (bare-LLM single prompt) and B2 (single ReAct agent), run INSIDE
the api container so they share the exact analyzers / evaluators / metric extraction
used by B3/B4 — the design proposal is the only thing that differs.

B1: one direct DeepSeek chat call with the StructuralDesignAgent system prompt
    (no tools, no ReAct, no loop). The proposal is then independently verified with
    the platform's FEAnalysisTool + EvaluationTool (paper §4.3: "事后用本系统有限元
    与规范校核独立评判"). This quantifies the compliance floor of an unguarded LLM.
B2: a single StructuralDesignAgent (holds tools, ReAct) run ONCE, no orchestration
    and no closed loop — isolates "multi-agent split" from "the closed loop".

Output rows match exp_client.py schema (same keys), so stats_pipeline.py ingests
results_B1.jsonl / results_B2.jsonl alongside results_B3/B4.

Usage (inside container, key resolved from exp_runner's encrypted DB record):
  docker exec -w /app structural-design-system-api-1 \
    python3 /app/experiments/baseline_runner.py --mode B1 \
      --testset /app/experiments/testset_e1.jsonl --reps 5 --out /app/experiments/results_B1.jsonl
"""
import argparse, json, time, os, asyncio, sys


def get_api_key(username="exp_runner"):
    from backend.database import get_db_context, User
    from backend.api.services.encryption_service import decrypt_api_key
    with get_db_context() as db:
        u = db.query(User).filter(User.username == username).first()
        return decrypt_api_key(u.api_key_encrypted)


def make_llm(api_key, task_suffix):
    from app.llm import LLM
    from app.config import LLMSettings
    cfg = LLMSettings(model="deepseek-chat", base_url="https://api.deepseek.com/v1",
                      api_key=api_key, api_type="openai", api_version="",
                      max_tokens=4000, temperature=0)
    name = f"baseline_{task_suffix}"
    return LLM(config_name=name, llm_config={name: cfg, "default": cfg})


def extract_proposal(text):
    """Mirror PlanningFlow._extract_design_proposal (pattern 2/3: balanced JSON w/ type)."""
    import re
    m = re.search(r'\{[\s\S]*?"type"[\s\S]*?\n\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            pass
    # balanced-brace fallback
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    chunk = text[start:i + 1]
                    if '"type"' in chunk:
                        try:
                            return json.loads(chunk)
                        except Exception:
                            break
                    break
        start = text.find("{", start + 1)
    return None


async def verify(design_proposal):
    """Independent verification = the SAME tools B3/B4 use. Returns metrics dict
    mirroring backend/tasks/design_task.py flattened_result['metrics']."""
    from structural_app.tool.fe_analysis_tool import FEAnalysisTool
    from structural_app.tool.evaluation_tool import EvaluationTool
    stype = design_proposal.get("type")
    fe = await FEAnalysisTool().execute(design_proposal=design_proposal)
    ar = json.loads(fe.output if hasattr(fe, "output") else str(fe))
    if ar.get("status") != "success":
        return {"compliant": None, "analysis_error": ar.get("error", "")[:200]}, ar
    cc = ar.get("code_check", {}) or {}
    ev = await EvaluationTool().execute(design_proposal=design_proposal, analysis_results=ar)
    er = json.loads(ev.output if hasattr(ev, "output") else str(ev))
    dims = er.get("dimensions") or {}
    econ = (dims.get("economy") or {}).get("indicators") or {}
    safe = (dims.get("safety") or {}).get("indicators") or {}
    sfs = cc.get("safety_factors") or {}
    score = er.get("comprehensive_score")
    metrics = {
        "compliant": cc.get("compliant"),
        "violations": len(cc.get("violations") or []),
        "score": score,
        "dims": {k: (v or {}).get("score") for k, v in dims.items()},
        "material_volume": econ.get("volume_m3"),
        "min_safety_factor": safe.get("min_safety_factor")
            if safe.get("min_safety_factor") is not None
            else (min(sfs.values()) if sfs else None),
        "safety_factors": sfs,
        # B1/B2 are single-shot: no closed loop, so the trajectory is flat at `score`.
        "score_history": [score, score, score] if score is not None else None,
    }
    return metrics, ar


async def run_b1(case, llm):
    """Bare LLM: one chat call with the design agent's system prompt, no tools/loop."""
    from structural_app.agent.structural_design_agent import StructuralDesignAgent
    from app.schema import Message
    sys_prompt = StructuralDesignAgent(llm=llm).system_prompt
    text = await llm.ask(messages=[Message.user_message(case["request"])],
                         system_msgs=[Message.system_message(sys_prompt)],
                         stream=False, temperature=0)
    proposal = extract_proposal(text if isinstance(text, str) else str(text))
    if not proposal:
        return dict(status="failed", error="no valid DesignProposal parsed from LLM output")
    metrics, _ = await verify(proposal)
    return dict(status="success", **metrics)


async def run_b2(case, llm):
    """Single ReAct agent holding all tools, run once — no orchestration, no loop."""
    from structural_app.agent.structural_design_agent import StructuralDesignAgent
    from app.tool.ask_human import AskHuman

    # Non-interactive AskHuman: authorize defaults instead of blocking on input().
    # Mirrors the scripted default path used for B3/B4, keeping B2 comparable and
    # preventing a hang in the headless container.
    class AutoAnswerAskHuman(AskHuman):
        async def execute(self, inquire: str) -> str:
            return "授权使用系统默认值，无需再次确认，请直接生成完整设计方案的JSON。"

    agent = StructuralDesignAgent(tools=[AutoAnswerAskHuman()], llm=llm)
    resp = await agent.run(case["request"])
    proposal = extract_proposal(resp if isinstance(resp, str) else str(resp))
    if not proposal:
        return dict(status="failed", error="no valid DesignProposal parsed from agent run")
    metrics, _ = await verify(proposal)
    return dict(status="success", **metrics)


async def main_async(a):
    api_key = get_api_key(a.user)
    cases = [json.loads(l) for l in open(a.testset, encoding="utf-8") if l.strip()]
    if a.limit:
        cases = cases[:a.limit]
    done = set()
    if os.path.exists(a.out):
        for l in open(a.out, encoding="utf-8"):
            try:
                r = json.loads(l); done.add((r["case_id"], r["rep"]))
            except Exception:
                pass
        print(f"resume: {len(done)} runs already in {a.out}", flush=True)
    runner = run_b1 if a.mode == "B1" else run_b2
    print(f"mode={a.mode} cases={len(cases)} reps={a.reps}", flush=True)
    with open(a.out, "a", encoding="utf-8") as f:
        for c in cases:
            for rep in range(1, a.reps + 1):
                if (c["case_id"], rep) in done:
                    continue
                llm = make_llm(api_key, f"{a.mode}_{c['case_id']}_{rep}")
                t0 = time.time()
                print(f"[{time.strftime('%H:%M:%S')}] {c['case_id']} rep{rep} ({a.mode}) ...", flush=True)
                try:
                    res = await runner(c, llm)
                except Exception as e:
                    res = dict(status="error", error=str(e)[:300])
                res.update(case_id=c["case_id"], rep=rep, type=c["type"],
                           scenario=c["scenario"], tag=a.mode, exp_mode=a.mode,
                           wall_s=round(time.time() - t0, 1))
                f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
                print(f"    -> {res['status']} score={res.get('score')} "
                      f"compliant={res.get('compliant')}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["B1", "B2"])
    ap.add_argument("--testset", required=True)
    ap.add_argument("--user", default="exp_runner")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    asyncio.run(main_async(a))


if __name__ == "__main__":
    main()

