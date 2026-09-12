# 2026-09-11 第一轮重跑结果

本轮从头生成，没有复用旧讲义。生成模型为 ModelScope `deepseek-ai/DeepSeek-V4-Pro-0813`，裁判为 Agnes `agnes-3.0-flash`；两个接口预检通过。

计划9组，实际生成18份讲义。仅1组完成两次匿名换序评分，8组评分失败：5组JSONDecodeError，3组LLMClientError。失败回复完整保留，不人工补分，不剔除后宣传整体效果。

唯一有效样本为TCP三次握手/考试强化，四维适配均分差值为+1.75（5分量表上的分差），事实准确性评分差值为0。**有效率只有1/9，该数值不能代表全体样本，不能作为画像增益已经得到验证的参赛结论。**

| 编号 | 主题 | 合成画像 | 状态 | 失败类型 |
|---|---|---|---|---|
| 1 | TCP 三次握手 | 基础补齐 | failed | JSONDecodeError |
| 2 | TCP 三次握手 | 考试强化 | complete | — |
| 3 | TCP 三次握手 | 工程实践 | failed | JSONDecodeError |
| 4 | 子网划分与子网掩码 | 基础补齐 | failed | LLMClientError |
| 5 | 子网划分与子网掩码 | 考试强化 | failed | LLMClientError |
| 6 | 子网划分与子网掩码 | 工程实践 | failed | LLMClientError |
| 7 | DNS 域名解析过程 | 基础补齐 | failed | JSONDecodeError |
| 8 | DNS 域名解析过程 | 考试强化 | failed | JSONDecodeError |
| 9 | DNS 域名解析过程 | 工程实践 | failed | JSONDecodeError |

下一步需先修复裁判结构化输出可靠性，再用本轮18份原始讲义重新进行全组评分，避免重复生成与挑选结果。当前不能确认是输出截断还是模型格式错误，因为现有客户端未保存finish_reason；不能凭JSON错误推断原因。保留本轮作为原始运行记录。

原始证据见同目录manifest.json、preflight.json、case_01.json至case_09.json和summary.json。模型评分不是教师独立复核，也不是学生学习效果实验。
