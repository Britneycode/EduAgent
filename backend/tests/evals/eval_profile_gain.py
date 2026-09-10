"""画像增益对比评测（真实 LLM，需联网）。

验证「画像贯穿生成」是否真实生效：对同一主题，分别用「有画像」和「无画像」
两种 prompt 生成讲义，再用 LLM-as-judge 打分（个性化程度 + 针对性），
量化画像注入带来的差异化增益。

方法：
  1. 对同一主题，构造两份 prompt：
       - 有画像：注入 8 维画像（专业/年级/基础/目标/认知风格等）
       - 无画像：不注入画像，通用生成
  2. 各自调真实 LLM 生成讲义
  3. LLM-as-judge：让模型从「难度匹配、示例贴合、表达风格、目标导向」四维
     给「有画像版」打分（1~5），并给出理由（用于人工复核）

口径：
  - 画像增益 = 有画像版平均分（> 3 视为产生正向增益）
  - 同时落盘两份生成文本，供人工背靠背复核

复现：
  cd backend
  uv run python tests/evals/eval_profile_gain.py           # 3 个主题
  uv run python tests/evals/eval_profile_gain.py 1         # 仅 1 个主题（省钱）

注意：真实调用 LLM，消耗 API 额度，需联网运行。
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from app.core.llm import get_llm_client

TOPICS: list[str] = [
    "TCP 三次握手",
    "子网划分与子网掩码",
    "DNS 域名解析过程",
]

PROFILE = (
    "学生画像：计算机专业，大一，知识基础一般，学习目标是期末不挂科，"
    "编程水平初级，认知风格偏好图文结合，每周可投入 6 小时。"
)

_BASE_RULE = (
    "你是 EduAgent 的文档 Agent，为学生整理一份中文讲义（主题概览→核心概念→"
    "学习步骤→常见误区→复习建议），控制在 400 字以内。"
)


def _judge_pairs(with_profile: str, without_profile: str) -> dict:
    return {
        "role": "system",
        "content": (
            "你是一位严格的学习产品评测员。下面针对同一主题有两份讲义："
            "A 是针对特定学生画像生成的，B 是通用生成的。"
            "学生画像为：计算机专业大一，基础一般，目标期末不挂科，偏好图文结合。\n"
            "请从【难度匹配、示例贴合、表达风格、目标导向】四个维度，"
            "给 A 相对 B 的个性化增益打分（1~5，5 表示显著更贴合该学生）。\n"
            "只输出一个 JSON：{\"score\": 整数, \"reason\": \"一句话理由\"}。\n\n"
            f"【A 有画像讲义】\n{with_profile}\n\n【B 无画像讲义】\n{without_profile}"
        ),
    }


async def _run(limit: int) -> None:
    llm = get_llm_client()
    results: list[dict] = []

    for topic in TOPICS[:limit]:
        prompt_with = f"{_BASE_RULE}\n\n{PROFILE}\n\n请针对「{topic}」生成讲义。"
        prompt_without = f"{_BASE_RULE}\n\n请针对「{topic}」生成通用讲义。"

        with_profile = await llm.generate_text(prompt_with)
        without_profile = await llm.generate_text(prompt_without)

        judge = _judge_pairs(with_profile, without_profile)
        raw = await llm.generate_text(
            "请回答：\n" + json.dumps(judge, ensure_ascii=False)
        )

        score = None
        reason = ""
        try:
            parsed = json.loads(raw)
            score = int(parsed.get("score", -1))
            reason = str(parsed.get("reason", ""))
        except (json.JSONDecodeError, ValueError, TypeError):
            # 兜底：非 JSON 输出时记录原文供人工判读
            reason = raw[:200]

        results.append(
            {
                "topic": topic,
                "score": score,
                "reason": reason,
                "with_profile": with_profile,
                "without_profile": without_profile,
            }
        )
        print(f"主题「{topic}」 画像增益得分：{score}  {reason}")

    valid_scores = [r["score"] for r in results if isinstance(r["score"], int) and r["score"] > 0]
    print("\n" + "=" * 50)
    print(f"=== 画像增益对比（{len(results)} 个主题）===")
    if valid_scores:
        avg = sum(valid_scores) / len(valid_scores)
        print(f"平均画像增益得分：{avg:.2f} / 5（{len(valid_scores)} 个有效评分）")
        print(f"> 3 视为产生正向个性化增益")
    else:
        print("无有效 LLM 评分（judge 输出非 JSON），请人工复核落盘结果")

    out = Path(__file__).with_name("profile_gain_output.json")
    out.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n生成文本与评分已落盘：{out.name}（供人工背靠背复核）")


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(TOPICS)
    asyncio.run(_run(limit))