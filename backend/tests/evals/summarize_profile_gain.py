"""从原始评分重新计算报告及引文审计，不调用模型。"""
import json
import re
import sys
from pathlib import Path
from statistics import mean

DIMS = ['难度匹配','示例贴合','表达适配','目标可执行性','事实准确性']
base = Path(sys.argv[1])
results = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(base.glob('case_*.json'))]
valid = [r for r in results if r['status']=='complete']
audit=[]
rows=[]
scores={'with_profile': [], 'without_profile': []}
order_gaps=[]
for r in valid:
    per_order=[]
    for j in r['judgments']:
        averages={}
        for label,condition in j['mapping'].items():
            content=re.sub(r'\s+','',r['generations'][condition]['content'])
            averages[condition]=mean(j['parsed'][label][d]['score'] for d in DIMS[:4])
            for dim in DIMS:
                item=j['parsed'][label][dim]
                audit.append({'case':r['id'],'order':len(per_order)+1,'condition':condition,'dimension':dim,'evidence':item['evidence'],'matches':re.sub(r'\s+','',item['evidence']) in content})
        per_order.append(averages['with_profile']-averages['without_profile'])
    order_gaps.append(abs(per_order[0]-per_order[1]))
    for condition in scores:
        scores[condition].append(mean(r['scores'][condition][d] for d in DIMS[:4]))
    rows.append(f"| {r['id']} | {r['topic']} / {r['profile']['id']} | {scores['without_profile'][-1]:.3f} | {scores['with_profile'][-1]:.3f} | {r['gain']:+.3f} | {r['accuracy_delta']:+.2f} | {order_gaps[-1]:.2f} |")
(base/'citation_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
if not valid: raise SystemExit('没有完整评分')
with_avg=mean(scores['with_profile']); without_avg=mean(scores['without_profile'])
positive=sum(r['gain']>0 for r in valid); negative=sum(r['gain']<0 for r in valid)
matched=sum(a['matches'] for a in audit)
attempts=[a for r in results for j in r['judgments'] for a in j.get('attempts',[])]
failures=[a for a in attempts if a.get('error_type')]
text=f'''# 画像增益补评结果（探索性模型评审）

本轮复用20260911-002343的18份讲义，未重新生成。生成模型：ModelScope deepseek-ai/DeepSeek-V4-Pro-0813；裁判：agnes-3.0-flash。合成画像3类、主题3个，计划9对，完成{len(valid)}/9对。

## 实测汇总

- 四维适配均分：无画像{without_avg:.3f}/5，有画像{with_avg:.3f}/5，分差{with_avg-without_avg:+.3f}（量表分差，不是学习成绩提升率）。
- 正/平/负增益：{positive}/{len(valid)-positive-negative}/{negative}对。
- 事实准确性模型评分差：{mean(r['accuracy_delta'] for r in valid):+.3f}。
- 两次换序的增益绝对差：平均{mean(order_gaps):.3f}，最大{max(order_gaps):.3f}。不能把换序评分当成独立学生样本。
- 裁判调用尝试{len(attempts)}次，其中失败尝试{len(failures)}次；所有原始尝试保留，使用每次首次合法评分，不按分数挑选。
- 引文连续匹配（仅忽略空白）：{matched}/{len(audit)}。未匹配引文{len(audit)-matched}条全部见citation_audit.json；它们可能是改写、拼接、标点差异或错误引文，未经教师逐项确认。不能将格式成功等同于证据有效。

| 编号 | 主题 / 画像 | 无画像 | 有画像 | 适配分差 | 事实分差 | 换序分差 |
|---|---|---|---|---|---|---|
'''+ '\n'.join(rows)+'''

## 方法与限制

每对使用实际DocAgent提示词、同一知识正文和篇幅要求，仅画像条件不同；不是检索能力、remio端到端或真人学习成效测试。画像为合成，样本数量小，三主题共享同一模型与课程。温度0.7；评分维度与1至5分锚点保持原协议。修复仅涉及JSON模式、8192输出上限、短引文/短理由、串行请求和最多3次重试。不能据此声称统计显著或学生成绩提升。

固定正文中TCP状态命名存在LAST_WAIT/LAST_ACK不一致，本次未修改材料。事实准确性仍是模型评分，需教师或RFC核验。引文核验只核实文字存在，不证明该引文支持裁判结论。由于裁判有换序波动及引文不匹配，结果只支持“当前模型评审下的适配倾向”，不构成独立教育效果验证。

证据：manifest.json（模型、参数、代码哈希）、case_01.json至case_09.json（原始讲义、映射、评分与每次尝试）、summary.json、citation_audit.json。复用内容逐项与原轮校验；失败及负结果不删除。
'''
(base/'RESULT.md').write_text(text,encoding='utf-8')
print(text[:1500])
