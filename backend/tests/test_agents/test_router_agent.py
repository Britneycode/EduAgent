from app.agents.router_agent import RouterAgent

DEFAULT_RESOURCES = ["document", "quiz", "code", "mindmap", "reading"]


def test_router_marks_profile_and_doc_for_learning_request() -> None:
    agent = RouterAgent()

    decision = agent.route("我是计算机专业大三学生，想复习反向传播")

    assert decision.update_profile is True
    assert decision.generate_document is True
    assert decision.topic == "反向传播"
    assert decision.resource_types == DEFAULT_RESOURCES


def test_router_updates_profile_when_user_shares_background() -> None:
    agent = RouterAgent()

    decision = agent.route("我的专业是数学，大二，基础一般，目标是准备期末")

    assert decision.update_profile is True
    assert decision.generate_document is True
    assert decision.topic == "准备期末"
    assert decision.resource_types == DEFAULT_RESOURCES


def test_router_generates_document_for_document_request() -> None:
    agent = RouterAgent()

    decision = agent.route("请帮我整理一下梯度下降的学习笔记")

    assert decision.update_profile is False
    assert decision.generate_document is True
    assert decision.topic == "梯度下降"
    assert decision.resource_types == DEFAULT_RESOURCES


def test_router_falls_back_to_document_for_normal_learning_question() -> None:
    agent = RouterAgent()

    decision = agent.route("帮我整理一下反向传播")

    assert decision.update_profile is False
    assert decision.generate_document is True
    assert "反向传播" in decision.topic
    assert decision.resource_types == DEFAULT_RESOURCES
