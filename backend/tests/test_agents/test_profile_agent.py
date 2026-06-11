from __future__ import annotations

from app.agents.profile_agent import ProfileAgent


def test_profile_agent_extracts_major_grade_goal_and_style() -> None:
    agent = ProfileAgent()

    update = agent.extract_profile_update(
        "我是计算机专业大三学生，机器学习基础一般，想复习反向传播，最好图文结合"
    )

    assert update["major"] == "计算机专业"
    assert update["grade"] == "大三"
    assert update["learning_goal"] == "复习"
    assert update["cognitive_style"] == "图文结合"
    assert update["knowledge_base"] == {"机器学习": "一般"}


def test_profile_agent_extracts_learning_pace_coding_level_and_weekly_hours() -> None:
    agent = ProfileAgent()

    update = agent.extract_profile_update(
        "我学得比较慢，编程水平初级，每周大概能学6小时"
    )

    assert update["learning_pace"] == "较慢"
    assert update["coding_level"] == "初级"
    assert update["weekly_hours"] == 6


def test_profile_agent_returns_empty_update_when_nothing_is_recognized() -> None:
    agent = ProfileAgent()

    update = agent.extract_profile_update("今天天气不错，我们开始吧")

    assert update == {}
