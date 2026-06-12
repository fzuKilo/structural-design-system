# 实验装置使用说明（experiment_kit）

## ⚠️ 安全提醒（先做这个）
部署在公网IP的管理员账号 admin/123456 极易被扫库爆破，且本次已在对话中明文传输。
请立即：改强密码、为实验单独建低权限账号、有条件时加IP白名单或挂到内网/VPN后。

## 文件清单
- `benchmark_repro.py` — 标准算例独立复现（已在Claude沙箱真实运行，结果见论文5.1节更新）
- `testset_e1.py` / `testset_e1.jsonl` — E1测试集生成器与44个案例
- `exp_client.py` — 远程实验客户端（在你们能访问8.155.172.84的机器上跑）
- `stats_pipeline.py` — 统计管线，直接产出论文格式表格

## 执行顺序
1. **核对API**（10分钟）：浏览器F12打开前端跑一次完整设计，对照Network面板修正
   exp_client.py顶部ENDPOINTS的4个路径与字段名（标记★ADJUST_HERE处）。
2. **冒烟测试**：`python exp_client.py --base http://8.155.172.84:8080 --user <实验账号> --pwd <密码> --testset testset_e1.jsonl --mode loop --reps 1 --out smoke.jsonl`
   先跑通1个案例，确认result_json里有score/compliant/score_history/material_volume字段。
   **若material_volume/min_safety_factor为None：需在后端result_json持久化中补这两个字段**（论文4.2节明确要求，5.2节客观指标交叉验证依赖它们）。
3. **正式E1/E2**（预计：44案例×10重复×2配置×~2.5min ≈ 37小时墙钟，可分多机/多晚断点续跑）：
   - B4: `--mode loop --tag B4 --reps 10 --out results_B4.jsonl`
   - B3: `--mode single --tag B3 --reps 10 --out results_B3.jsonl`（若后端无mode开关，在配置中关闭两个闭环节点后跑）
   - B1: 裸LLM基线无需走平台——直接调DeepSeek API单提示生成JSON，再用平台的"仅分析"接口或本地analyzer校核（可让学生基于benchmark_repro.py的建模函数扩展）
4. **消融E3**：服务器侧逐项关闭（A1关Node1 / A2关Node2 / A3关RAG / A4去约束规则），各用`--tag A1..A4 --reps 5`重跑。A4务必保留对话日志。
5. **跨模型E4**：服务器配置切换模型，`--tag GPT4o`等，代表性子集（每类2案例）即可。
6. **统计**：`python stats_pipeline.py results_B3.jsonl results_B4.jsonl ...` → stats_report.md，
   表格直接对应论文5.2/5.3节回填区。
7. 数据发回给Claude，完成图表重绘（figures/scripts模板）与正文定量结论更新。

## 成本预算
按论文5.2.3实测均值0.048元/任务：E1+E2全量≈880次×0.05≈45元；E3+E4≈25元。合计<100元。
