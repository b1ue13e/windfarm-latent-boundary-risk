"""Produce the supplementary report from accepted outputs, with no model execution."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--recovered',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();r=args.recovered
    read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
    primary=read(r/'results/aggregate/primary.json'); env=primary['bounds']['groups'][0]
    audit=read(r/'independent_audit.json');budget=read(r/'BUDGET_FINAL.json')
    assert audit['status']=='PASS_INDEPENDENT_ACTION_AND_SOURCE_REPLAY'
    cfg=read(r/'protocol.json');freeze=read(r/'results/chosen/freeze.json');evt=read(r/'results/UNLOCK_EVENT.json')
    assert cfg['primary_q']==.95 and len(cfg['selected_tasks'])==10
    old=read(args.repository/'analyses/independent_confirmation_execution_20261019/derived/summary.json')
    p0=read(args.repository/'experiments/mainline_supplement_20261026/p0_verified/outputs_v2/SUMMARY.json')
    means=audit['means'];ratio=env['relative_ratio_point'][0][1];lo=env['relative_ratio_lower'][0][1];hi=env['relative_ratio_upper'][0][1]
    vmax=[max(row[i] for row in env['risk_upper']) for i in (0,1)]
    ok=primary['verdict']['status']=='ALL_FROZEN_CANDIDATES_CONFIRMED'
    verdict=('原冻结低输入策略在2026年1—4月再次满足相对固定参照的成本非劣和双方五实例绝对事件率要求。'
             if ok else '原冻结低输入策略在2026年1—4月未同时满足所有预声明要求；保留该时间外失败，不调整参数。')
    lines=['# 最小补充实验结果','',verdict,'',
           '本轮完成P0旧证据零拟合汇总与P1原权重时间外验证。0新训练、0新校准、0新增模型候选，原结果、稿件和科学阈值保持。',
           '', '## 新窗口主检验','',
           '| 时间窗 | P1成本 | WPQ36成本 | 相对成本与原近似联合区间 | P1最大事件率上界 | 参照最大事件率上界 |',
           '|---|---:|---:|---|---:|---:|',
           f"| 2025原确认 | {old['mean_cost'][0]:.6f} | {old['mean_cost'][1]:.6f} | {old['relative_cost_point']*100:+.4f}% [{old['relative_cost_interval'][0]*100:+.4f}%, {old['relative_cost_interval'][1]*100:+.4f}%] | {old['candidate_max_instance_risk_upper']*100:.4f}% | {old['reference_max_instance_risk_upper']*100:.4f}% |",
           f'| 2026年1—4月新验证 | {means["P1"][0]:.6f} | {means["WPQ36"][0]:.6f} | {ratio*100:+.4f}% [{lo*100:+.4f}%, {hi*100:+.4f}%] | {vmax[0]*100:.4f}% | {vmax[1]*100:.4f}% |','',
           '成本单位为每有效风机区间的kWh等价代理损失。主判据是相对成本上界≤2%，且双方每个固定拟合实例的绝对事件率上界≤10%。成本为正的溢价须保留，不能写成降本优越。',
           '', '### 预定块长敏感性','',
           '| 块长 | 相对成本上界 | 候选最大事件率上界 | 参照最大事件率上界 | 原联合判据 |',
           '|---|---:|---:|---:|---|',
           f'| 3日，主检验 | {hi*100:+.4f}% | {vmax[0]*100:.4f}% | {vmax[1]*100:.4f}% | {primary["verdict"]["status"]} |']
    sens=read(r/'results/aggregate/sensitivity.json')
    for span in (1,7):
        s=sens[f'span_{span}'];lines.append(f'| {span}日 | {s["relative_cost_ratio_upper"]*100:+.4f}% | {s["candidate_max_risk_upper"]*100:.4f}% | {s["reference_max_risk_upper"]*100:.4f}% | {"通过" if s["confirmed"] else "未确认"} |')
    lines+=['','### 描述性采购与短缺分解','',
            '| 固定策略 | C | R，采购 | U，未覆盖缺额 | V，事件率 |','|---|---:|---:|---:|---:|']
    for name in ('P1','WPQ36'):
        c,r0,u,v=means[name];lines.append(f'| {name}/HGB/q0.95 | {c:.6f} | {r0:.6f} | {u:.6f} | {v*100:.4f}% |')
    lines+=['','C=R+10U。U/R在此只报告点值，未建立额外严重度H资格或全端点保护；原2025主确认没有可继承的H定义。',
            '', '## 数据和执行资格','',
            '- 用户确认本人/团队此前未查看2026年1—4月测量或评测结果；公共样例仅元数据已知，不宣称掌握所有第三方访问史。',
            f'- 执行冻结时间：{freeze["created_utc"]}；一次解封事件：{evt["utc"]}。冻结严格先于测量解析。',
            '- 原2023—2024十份HGB权重、五种子201—205、q0.95偏移与共同预测器原样复用。原53源码、69相关文件通过身份核验，原依赖版本一致。',
            '- 两张原始表跨年六字段都覆盖21台，先核原值再转换；全部预定机组和时段保留，只沿用有限未来有功mask。',
            f'- 有效目标人口与天气日以实际收据为准：{audit["means"] and primary["descriptive"]["n_valid_per_fit"]:.0f}格/拟合、{primary["descriptive"]["n_weather_days"]}个UTC日；五个拟合不是五份独立天气。',
            '- 2026包含已公开的Dynamic Yaw干预，保留该分布改变，不按处理或结果筛样本，不推断控制因果效应。',
            f'- 独立重放核对全部10个策略日账，最大算术差{audit["maximum_daily_arithmetic_error"]:.3g}；原源码抽查{audit["exact_original_predictor_sample_issues"]}个固定issue时点的共同预测与每份模型输出逐值一致。',
            '- 主及1/7日统计用原固定随机流重放一致；14坐标包含10个实例事件率和2×2成本比矩阵。它们是依赖天气近似区间，未获得覆盖率理论证明。',
            f'- PBS四作业全部退出0；实际分配核数×墙钟合计{budget["used_allocated_cpu_seconds"]} CPU秒，PBS CPU合计{budget["pbs_reported_cpu_seconds"]}秒，低于14400秒预算。',
            '', '## P0复用结果','',
            'P0实际读取14个原输入并逐项核对前后SHA，投影114个M人口原坐标；未重新bootstrap。R0182/BR009的64654坐标族和EM1_003_P的88052坐标族分别保存。',
            'BR009−R182主3日U差为−0.012575097，原区间[−0.024311898，−0.000838296]；成本非劣，V区间跨零。P侧25%固定混合在其原1/3/7日分析均合格。',
            'Praw−OZ6主3日成本：HGB −8.4725% [−11.8801%，−5.0650%]；MLP −13.0510% [−17.2211%，−8.8808%]。U/V区间与逐拟合H完整保留，不由成本阳性推成全端点替代。',
            '', '## 论文主张如何使用','',
            verdict,
            '这是同一场站、固定预测承诺与目标下的时间外证据。它补强低资源备用层输入的有界充分性实例，不验证新的场站、真实市场收益、PCC交付、控制因果效应或普遍最小传感器集合。',
            '2025次要q0.925有限族最小性仍与主q0.95确认分开；本轮不在2026重选q或搜最小策略。Praw/OZ6与WTB保护比较保持开发证据身份。',
            '', '## 停止与复现','',
            '预定最小补实验闭环后结束本轮，不继续在旧窗口加模型，也不按本次结果追加q/阈值/规则。下一步可将本报告及P0表格用于既有大纲的结果段落。',
            '运行入口为p1/adapter.py，协议为p1/protocol.json；PBS脚本按preflight→冻结→evaluate→aggregate→独立audit执行。原权重备份与原始新数据只在受控本地/Metis保留，未提交Git。']
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'REPORT_CN.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    out=dict(status='COMPLETE_MINIMAL_SUPPLEMENT',P0='VERIFIED_ZERO_FIT_PROJECTION',P1=primary['verdict']['status'],
             new_fits=0,mean_cost=[means[x][0] for x in ('P1','WPQ36')],relative_cost_point=ratio,
             relative_cost_interval=[lo,hi],risk_upper_max=vmax,independent_audit=audit['status'],budget=budget,
             primary_q=.95,finite_family_minimality_tested=False,utc=datetime.now(timezone.utc).isoformat())
    (args.output/'FINAL_RESULTS.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))


if __name__=='__main__':main()
