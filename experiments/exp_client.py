# -*- coding: utf-8 -*-
"""E1-E4 experiment client — runs against the LOCAL deployment (http://localhost:8000).

Endpoints/fields verified against backend/api/routes/{auth,design}.py:
  login   POST /api/auth/login           {username,password} -> {access_token}
  create  POST /api/design/create        {request_text, exp_mode} -> {id}
  status  GET  /api/design/{id}/status   -> {status, result_json}
  pending GET  /api/design/{id}/pending-ask -> {pending, ask_human}
  respond POST /api/design/{id}/respond  {answer}

exp_mode drives the closed-loop configuration server-side (deterministic, no manual
answers needed): B4(full loop, default) / B3(open loop) / A1..A4(ablations).
The pending-ask auto-answer below is a SAFETY NET for the model-confirmation /
default-value prompts that exp_mode does not short-circuit.

Usage:
  pip install requests
  python exp_client.py --base http://localhost:8000 --user exp_runner --pwd ExpRunner2026 \
      --testset testset_e1.jsonl --exp-mode B4 --reps 1 --tag B4 --out results_B4.jsonl

Resume-safe: completed (case_id, rep) rows in --out are skipped; Ctrl-C is safe.
"""
import argparse, json, time, sys, os, re
import requests

EP = {
    "login":   "/api/auth/login",
    "create":  "/api/design/create",
    "status":  "/api/design/{tid}/status",
    "pending": "/api/design/{tid}/pending-ask",
    "respond": "/api/design/{tid}/respond",
}
POLL_S, TASK_TIMEOUT_S = 4, 1200

# Auto-answers for prompts exp_mode does NOT short-circuit (model confirmation,
# default-value authorization). Node1/Node2 decisions are handled server-side by
# exp_mode, but we keep code-check/eval mappings here as a fallback if exp_mode is
# unset. Matched by regex against the question text; first match wins.
DEFAULT_ANSWERS = [
    (r"导出BIM|Speckle|IFC", "n"),
    (r"规范.*未通过|不满足|违规|校核未通过|处理方式", "auto"),
    (r"预警|后续操作|优化", "optimize"),
    (r"确认|预览|模型.*(正确|无误)|是否继续", "确认"),
    (r"选择.*方案|方案对比|候选", "__BEST_SCHEME__"),
    (r"默认值|补全|参数缺失", "授权使用默认值，直接生成方案"),
]


def login(s, base, user, pwd):
    r = s.post(base + EP["login"], json={"username": user, "password": pwd}, timeout=20)
    r.raise_for_status()
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError(f"login returned no access_token: {r.text[:200]}")
    s.headers["Authorization"] = f"Bearer {tok}"
    return tok


def pick_answer(ask):
    """Choose an answer string for a pending ask_human prompt."""
    question = ask.get("question", "") or ""
    options = ask.get("options") or []
    ctx = ask.get("context") or {}
    schemes = ctx.get("proposals") or ctx.get("schemes") or ctx.get("candidates")
    if schemes:  # multi-scheme selection: pick highest score
        def _score(x):
            m = x.get("metrics") or {}
            return x.get("score", m.get("total_score", m.get("comprehensive_score", 0)) or 0)
        best = max(schemes, key=_score)
        return best.get("name") or best.get("id") or str(schemes.index(best) + 1)
    for pat, ans in DEFAULT_ANSWERS:
        if re.search(pat, question):
            if ans == "__BEST_SCHEME__":
                return options[0] if options else "1"
            # if options exist, map keyword answer onto the matching option text
            if options:
                for o in options:
                    if ans[:2] in str(o):
                        return str(o).split(" - ")[0].split(" ")[0]
            return ans
    return (options[0].split(" - ")[0] if options else "确认")


def run_task(s, base, case, exp_mode, tag):
    r = s.post(base + EP["create"],
               json={"request_text": case["request"], "exp_mode": exp_mode}, timeout=30)
    r.raise_for_status()
    tid = r.json().get("id") or r.json().get("task_id")
    t0, answered = time.time(), set()
    while time.time() - t0 < TASK_TIMEOUT_S:
        st = s.get(base + EP["status"].format(tid=tid), timeout=20).json()
        status = st.get("status")
        # answer any pending human prompt (model-confirm / default-value / fallback)
        try:
            pa = s.get(base + EP["pending"].format(tid=tid), timeout=15).json()
        except Exception:
            pa = {}
        if pa.get("pending") and pa.get("ask_human"):
            ask = pa["ask_human"]
            key = ask.get("question", "") + str(ask.get("stage", ""))
            if key not in answered:
                ans = pick_answer(ask)
                s.post(base + EP["respond"].format(tid=tid),
                       json={"answer": ans}, timeout=15)
                answered.add(key)
        if status in ("success", "failed"):
            rj = st.get("result_json") or {}
            m = rj.get("metrics") or {}
            return dict(task_id=tid, status=status, exp_mode=exp_mode, tag=tag,
                        wall_s=round(time.time() - t0, 1),
                        error=st.get("error"),
                        compliant=m.get("compliant"),
                        violations=m.get("violations_count"),
                        score=m.get("comprehensive_score"),
                        dims=m.get("dimension_scores"),
                        score_history=m.get("score_history"),
                        material_volume=m.get("material_volume"),
                        min_safety_factor=m.get("min_safety_factor"),
                        safety_factors=m.get("safety_factors"),
                        llm_model=m.get("llm_model"))
        time.sleep(POLL_S)
    return dict(task_id=tid, status="timeout", exp_mode=exp_mode, tag=tag,
                wall_s=round(time.time() - t0, 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--user", required=True)
    ap.add_argument("--pwd", required=True)
    ap.add_argument("--testset", required=True)
    ap.add_argument("--exp-mode", dest="exp_mode", default="B4",
                    help="B4(full loop)/B3(open loop)/A1/A2/A3/A4")
    ap.add_argument("--reps", type=int, default=10)
    ap.add_argument("--tag", default=None, help="defaults to exp-mode")
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0, help="only first N cases (smoke)")
    a = ap.parse_args()
    tag = a.tag or a.exp_mode
    out = a.out or f"results_{tag}.jsonl"

    cases = [json.loads(l) for l in open(a.testset, encoding="utf-8") if l.strip()]
    if a.limit:
        cases = cases[:a.limit]
    done = set()
    if os.path.exists(out):
        for l in open(out, encoding="utf-8"):
            try:
                r = json.loads(l); done.add((r["case_id"], r["rep"]))
            except Exception:
                pass
        print(f"resume: {len(done)} runs already recorded in {out}")

    s = requests.Session()
    login(s, a.base, a.user, a.pwd)
    print(f"logged in as {a.user}; exp_mode={a.exp_mode} tag={tag} cases={len(cases)} reps={a.reps}")

    with open(out, "a", encoding="utf-8") as f:
        for c in cases:
            for rep in range(1, a.reps + 1):
                if (c["case_id"], rep) in done:
                    continue
                print(f"[{time.strftime('%H:%M:%S')}] {c['case_id']} rep{rep} ({tag}) ...", flush=True)
                try:
                    res = run_task(s, a.base, c, a.exp_mode, tag)
                except Exception as e:
                    res = dict(status="error", error=str(e)[:300], exp_mode=a.exp_mode, tag=tag)
                res.update(case_id=c["case_id"], rep=rep, type=c["type"], scenario=c["scenario"])
                f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
                print(f"    -> {res['status']} score={res.get('score')} "
                      f"compliant={res.get('compliant')} sh={res.get('score_history')} "
                      f"vol={res.get('material_volume')} minSF={res.get('min_safety_factor')}")


if __name__ == "__main__":
    main()
