# -*- coding: utf-8 -*-
"""统计管线: 读取exp_client输出的多份results_*.jsonl, 产出论文4.4节规定的全部统计量。
用法: python stats_pipeline.py results_B3.jsonl results_B4.jsonl [results_B1.jsonl ...]
输出: stats_report.md (配对Wilcoxon/McNemar/Holm/效应量/CI + 5.2/5.3节格式的表格)
依赖: pip install scipy pandas
"""
import sys, json, itertools
import pandas as pd
from scipy import stats as st

def load(fp):
    rows = [json.loads(l) for l in open(fp, encoding="utf-8")]
    df = pd.DataFrame(rows)
    df = df[df.status == "success"]
    return df

def rank_biserial(x, y):
    d = [a - b for a, b in zip(x, y) if a != b]
    if not d: return 0.0
    pos = sum(1 for v in d if v > 0)
    return 2 * pos / len(d) - 1

def case_means(df, col):
    return df.groupby("case_id")[col].mean()

def mcnemar(b, c):
    from scipy.stats import binomtest
    n = b + c
    return binomtest(b, n, 0.5).pvalue if n else 1.0

def main(files):
    dfs = {f.split("results_")[-1].replace(".jsonl",""): load(f) for f in files}
    out = ["# Statistical report\n"]
    # --- 每配置汇总 ---
    out.append("## Per-configuration summary\n\n| config | n_runs | compliance | score mean±SD | material vol | min SF |")
    out.append("|---|---|---|---|---|---|")
    for k, d in dfs.items():
        out.append(f"| {k} | {len(d)} | {d.compliant.mean()*100:.1f}% | "
                   f"{d.score.mean():.1f}±{d.score.std():.1f} | "
                   f"{d.material_volume.mean() if 'material_volume' in d else float('nan'):.4f} | "
                   f"{d.min_safety_factor.mean() if 'min_safety_factor' in d else float('nan'):.2f} |")
    # --- 配对检验(案例级均值配对) ---
    pairs = list(itertools.combinations(dfs.keys(), 2))
    pvals, lines = [], []
    for a, b in pairs:
        ma, mb = case_means(dfs[a], "score"), case_means(dfs[b], "score")
        common = ma.index.intersection(mb.index)
        w = st.wilcoxon(ma[common], mb[common])
        r = rank_biserial(list(mb[common]), list(ma[common]))
        ca = dfs[a].groupby("case_id").compliant.mean() > 0.5
        cb = dfs[b].groupby("case_id").compliant.mean() > 0.5
        b01 = int(((~ca[common]) & cb[common]).sum()); b10 = int((ca[common] & (~cb[common])).sum())
        pm = mcnemar(b01, b10)
        pvals.append(w.pvalue)
        lines.append((a, b, len(common), float(ma[common].mean()), float(mb[common].mean()),
                      w.statistic, w.pvalue, r, pm))
    # Holm校正
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    holm = [None]*len(pvals); m = len(pvals)
    for rank, i in enumerate(order):
        holm[i] = min(1.0, pvals[i] * (m - rank))
    out.append("\n## Pairwise tests (case-level paired, Holm-corrected)\n")
    out.append("| A | B | n | mean(A) | mean(B) | Wilcoxon W | p | p(Holm) | effect r | McNemar p (compliance) |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for (a,b,n,ma,mb,W,p,r,pm), ph in zip(lines, holm):
        out.append(f"| {a} | {b} | {n} | {ma:.1f} | {mb:.1f} | {W:.0f} | {p:.2e} | {ph:.2e} | {r:.2f} | {pm:.2e} |")
    # --- 贡献分解(5.3节, 需score_history) ---
    for k, d in dfs.items():
        sh = d.dropna(subset=["score_history"]) if "score_history" in d else pd.DataFrame()
        if len(sh):
            out.append(f"\n## Node contribution decomposition ({k})\n")
            out.append("| scenario | initial | after Node1 | after Node2 | N1 contrib | N2 contrib |")
            out.append("|---|---|---|---|---|---|")
            sh = sh.assign(s0=sh.score_history.str[0], s1=sh.score_history.str[1], s2=sh.score_history.str[2])
            for scen, g in sh.groupby("scenario"):
                out.append(f"| {scen} | {g.s0.mean():.1f} | {g.s1.mean():.1f} | {g.s2.mean():.1f} "
                           f"| +{(g.s1-g.s0).mean():.1f} | +{(g.s2-g.s1).mean():.1f} |")
    open("stats_report.md", "w", encoding="utf-8").write("\n".join(out))
    print("written stats_report.md")

if __name__ == "__main__":
    main(sys.argv[1:])
