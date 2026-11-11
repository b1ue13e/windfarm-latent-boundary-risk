"""Generate the review report from immutable compact pilot evidence."""
from pathlib import Path
import csv
import hashlib
import json

BASE = Path(__file__).resolve().parent


def load(name):
    return json.loads((BASE / name).read_text(encoding="utf-8"))


def main():
    s, h, a = load("summary.json"), load("historical_choices.json"), load("action_audit.json")
    env = load("development_envelopes.json")
    e = env["3"]
    nk = len(s["labels"])
    evidence = BASE / "evidence"
    rows, fit_seconds = [], []
    for i in range(70):
        receipt = json.loads((evidence / f"results/evaluation/{i}/receipt.json").read_text())
        fit = json.loads((evidence / f"results/fits/{i}/receipt.json").read_text())
        metrics = json.loads((evidence / f"results/evaluation/{i}/metrics.json").read_text())
        row = {k: receipt[k] for k in ("estimator", "cell", "seed")}
        row.update(task=i, q=h["choices"][f'{receipt["estimator"]}:{receipt["cell"]}']["q"], fit_rows=fit["fit_rows"],
                   fit_seconds=fit["fit_seconds"])
        for population, values in metrics.items():
            row.update({population + "_" + k: v for k, v in values.items()})
        rows.append(row)
        if receipt["estimator"] != "CONTROL":
            fit_seconds.append(fit["fit_seconds"])
    with (BASE / "instance_metrics.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    pct = lambda v: f"{100 * v:.3f}%"
    def ci(estimator, name):
        kind = "D" if name == "P_premium_vs_Z" else "G"
        return s["registered_intervals"][f"{estimator}:{name}|cost|{kind}"]
    lines = ["# Metis S2实跑结果与停止决定", "",
        "**决定：STOP_INVESTMENT_AT_S2。** 已完成60次主模型拟合及10个简单控制实例；两估计器均未通过预定A、B或完整三端点低增量C路线。本轮不启用备用配方、不扩S3—S5、不采新测量、不改论文。停止是本方案的投入决定，不能被改写成总体状态信息无用或现场不可用的证明。", "",
        "本研究是在已查看WTB窗口上的结果知情开发。拟合、offset、历史选档、开发计分时钟分离；新模型开发计分前已冻结历史选择。下列联合区间是近似天气块重采样界，不能按未见确认或现场风险保证解释。", "",
        "## 1. 主问题现在得到的有界答案", "",
        "在本次HGB程序中，强新鲜WPQ历史后加入当前pitch的平均代理成本点估计未改善；旧WPQ历史上更新功率的成本变化远大于更新pitch；当前功率已更新后再加pitch的成本点估计也未改善。F→FZ和OP6→OPZ6的成本收益上界均低于1%，但这只是特定已训练程序/计分人口的成本证据。相关策略风险资格没有全部通过，旧信息加pitch的效果区间又跨越重要差门槛，因此不能宣布通过有界低增量C或安全替代B。MLP不支持把HGB的精度界扩为跨估计器事实。", "",
        "| 已冻结比较 | HGB成本收益/溢价 | 95%近似联合区间 |", "|---|---:|---:|"]
    names = [("强历史→加pitch", "fresh_state"), ("旧历史→新鲜pitch", "old_state"),
             ("旧历史→新鲜功率", "old_power"), ("新鲜功率相对pitch成本溢价D", "P_premium_vs_Z"),
             ("新鲜功率后→再加pitch", "residual_state")]
    for title, name in names:
        x = ci("HGB", name)
        lines.append(f"| {title} | {pct(x['point'])} | [{pct(x['lower'])}, {pct(x['upper'])}] |")
    lines += ["", "G为正表示减少成本；D为负表示功率更新成本更低。它们均是已冻结训练及历史选档程序的整体效果，包括校准，不是Bayes纯信息值或pitch物理因果效应。", "",
        "HGB新鲜基线F历史选择q=.925，FZ选择q=.90，其余多数更新格q=.90；MLP F/FZ均q=.90。raw动作和offset后动作分解已保留，避免把历史风险档位变化全归因于新测量。HGB raw F/FZ成本同样没有pitch收益，不是只靠一个offset差造出的方向。", "",
        "## 2. 所有策略与风险资格", "",
        "| 策略 | 选档q | mean C | raw mean C | 实例事件率范围 | 最大实例风险联合上界 | 风险资格 |",
        "|---|---:|---:|---:|---:|---:|---|"]
    for k, label in enumerate(s["labels"]):
        est, cell = label.split(":")
        rr = [r for r in rows if r["estimator"] == est and r["cell"] == cell]
        raw = sum(r["raw_primary_C"] for r in rr) / 5
        risks = [r[k] for r in s["instance_risk"]]
        upper = max(e["upper"][j * nk + k] for j in range(5))
        lines.append(f"| {label} | {h['choices'][label]['q']} | {s['mean_cost'][k]:.6f} | {raw:.6f} | {pct(min(risks))}–{pct(max(risks))} | {pct(upper)} | {'PASS' if s['risk_qualified'][label] else '未通过'} |")
    lines += ["", "C单位为代理kWh/有效机组间隔。风险资格要求每一固定实例联合上界≤10%。未通过不等于所有策略的真实事件率已证明超过10%；例如一些样本事件率低于10%，但联合上界仍越界。HGB OZ6已有实例的样本事件率超过10%，应与其余不确定性情形区分。没有据此在开发段换q。", "",
        "## 3. 三条验收路线为何未过", "",
        "- **A重要状态增量：未过。** HGB F→FZ及OP6→OPZ6成本收益上界均低于1%，不存在达到重要差的正向证据；风险/缺额条件也未闭合。MLP对应区间跨界，不能作为HGB失败的替代主要结论。",
        "- **B功率替代状态：未过。** HGB旧信息加pitch收益下界仅0.494%，未超过1%；功率更新成本收益、相对pitch的低成本及小残余pitch收益只通过部分成本条件。相关风险、功率相对OPZ6等逐实例缺额守门未过，不能称可安全替代。",
        "- **C三端点低增量：未过。** HGB旧信息加pitch收益上界6.523%，不能把所有状态增量都界定到1%以内；更新策略风险资格亦未闭合。只能保留强历史/已更新功率两对的成本上界事实，不能升级成全部状态冗余。", "",
        "缺额守门H=10(U候选−U参照)/C*；C*在历史段冻结为" + f"{h['Cstar']:.9f}" + "，容限为0.1%。下面是各比较跨五实例的最大联合上界，不是平均效应：", "",
        "| 缺额方向 | HGB最大上界 | MLP最大上界 |", "|---|---:|---:|"]
    for title, name in [("FZ−F", "fresh_state"), ("OZ6−O6", "old_state"), ("OP6−O6", "old_power"),
                        ("OPZ6−OP6", "residual_state"), ("OP6−OZ6", "severity_P_vs_Z"), ("OP6−OPZ6", "severity_P_vs_PZ")]:
        vals = [max(v["upper"] for k, v in s["registered_intervals"].items() if k.startswith(f"{est}:{name}|severity")) for est in ("HGB", "MLP")]
        lines.append(f"| {title} | {pct(vals[0])} | {pct(vals[1])} |")
    lines += ["", "## 4. 完整性、敏感性与复用", "",
        f"VERIFIED：原始CSV SHA匹配，原始通道重读与归档逐值一致；主要配对计分{s['n_cells']:,}格，35个天气日，五实例共享训练行、预测、目标、掩码和重采样。完整训练索引、权重和动作留存Metis。", "",
        f"VERIFIED：本地41项相关测试通过；Metis预检13项通过；归档动作审计{a['records']}个人口/动作版本记录、{a['exact_and_tolerance_checks']}项检查通过。重建序列化动作及日账目，未重放权重推理。两项原有科学门禁通过，只检查原有主张/数字一致性，不认证新近似推断覆盖率或现场安全。", "",
        "历史联合族450坐标（350逐实例风险+100所有可能q的F/简单控制成本）；开发主族154坐标（70风险+14成本+70有符号缺额），各alpha=.05。20,000组共享圆形天气块，主跨度3天，1/7天为敏感性；从不把机组或种子当独立天气样本。所有14组均有历史合格选择，未删失不利格或换成q=.99兜底。", "",
        "块跨度敏感性（成本区间；不用于改选主要结论）：", "", "| 跨度/天 | HGB F→FZ | HGB O6→OZ6 | HGB O6→OP6 | HGB OP6→OPZ6 |", "|---:|---|---|---|---|"]
    for span in (3, 1, 7):
        z = env[str(span)]
        mapped = {"|".join(map(str, label)): j for j, label in enumerate(z["labels"])}
        cells = []
        for name in ("fresh_state", "old_state", "old_power", "residual_state"):
            ix = mapped[f"HGB:{name}|cost|G"]
            cells.append(f"[{pct(z['lower'][ix])}, {pct(z['upper'][ix])}]")
        lines.append("| " + str(span) + " | " + " | ".join(cells) + " |")
    lines += ["", "主1%标准保持；改看0.5%或2%也不能修复主3天族的风险/缺额未资格，不能用更宽容的成本尺度宣布通过。无零收益或信息冗余的总体判决。", "",
        f"训练工作量：60个主拟合，拟合墙钟时间合计{sum(fit_seconds):.2f}秒（并行任务fit计时之和，不是核时/账单）。CPU两线程，同步最多10作业；未使用GPU。每个fit实际360000共同有效行。首次路径预检244971失败后修复，未训练；失败原目录和日志保留。", "",
        "## 5. 四个问题与TSTE判断", "",
        "| 问题 | 本轮能说什么 | 尚未达到什么 |", "|---|---|---|",
        "| Why care | 测量通道和刷新时效应分开比较；成本下降与风险资格必须同时看 | 没有真实遥测延迟、采购接口或现场收益证明 |",
        "| What's new | 补上强WPQ历史后真实pitch、同槽功率/pitch与互补性的配对开发证据 | 不是已确认的普适替代规律；SETA全文方法排重仍不完整 |",
        "| Why believe | 来源/时钟/人口/五实例/冻结选档/联合推断/归档账目可审查，并如实保留失败 | 风险和缺额门没过；有限程序不裁决H1/H2/H3总体机制 |",
        "| Why TSTE | 问题与可再生能源风险决策有关 | 当前没有跨来源、组合净短缺、新窗口确认且资格通过的知识增量，不足以据此恢复TSTE扩展投入 |", "",
        "**当前建议：执行原停止规则，结束本轮S2扩展。** 不因为已经做得久而放宽风险/缺额、换选档或追加网络。保留这次公平对照与负结果；如果未来另立任务修复风险资格，应先说明新的科学对象与独立确认责任，不能把本轮重调结果重新称为首次检验。当前未证明研究方向永久无价值，但没有达到这份方案规定的继续门槛。", "",
        "UNKNOWN仍包括：新问题的未见确认样本及日历；真实运行质量/到达时钟/组合计量与采购责任；第二近邻全文的剩余方法重合。此次没有为补齐它们启动新工作。", "",
        "## 6. 审查入口", "",
        "- [冻结配置](protocol.json)、[人口与时钟](QUALIFICATION.md)、[逐实例raw/offset指标](instance_metrics.csv)。",
        "- [全部主结果及154坐标](summary.json)、[三种块跨度完整界](development_envelopes.json)、[历史选择](historical_choices.json)、[归档动作审计](action_audit.json)。",
        "- [调度历史](scheduler_history.json)、[导出清单](export_manifest.json)、[完整执行记录](EXECUTION.md)。",
        "- 部分派生证据包SHA256：9a184aab3d31b8b48f694400518ab6e8da5316610816ef334c9811a40d8f02cd；822个成员在本地逐文件验SHA和大小。它不是全量原始/动作/权重重放包；全量只读资产位于`/lstr/sahara/minlpml/junyu/state_measurement_pilot_20261020_v2/results`。", ""]
    (BASE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    protected = ["paper_tste_ieee.md", "paper_tste_supplementary.md", "paper_tste_chinese.md", "docs/SCIENTIFIC_CONTRACT.md"]
    repo = BASE.parents[1]
    save = dict(status="COMPLETED_DEVELOPMENT_STOP_AT_S2", new_main_fits=60, simple_instances=10,
                routes=s["outcomes"], compact_members_verified=822,
                compact_archive_sha256=hashlib.sha256((BASE / "compact_evidence.tar.gz").read_bytes()).hexdigest(),
                action_audit=a["status"], local_related_tests=41, metis_preflight_tests=13,
                protected_sha256={name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in protected},
                manuscript_changed=False, new_measurements_downloaded=False, further_stages_started=False)
    (BASE / "VERIFICATION.json").write_text(json.dumps(save, ensure_ascii=False, indent=2),encoding="utf-8",newline="\n")


if __name__ == "__main__":
    main()
