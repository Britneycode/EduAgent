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


def test_router_generates_only_code_for_code_practice_request() -> None:
    agent = RouterAgent()

    decision = agent.route("帮我写一个反向传播的 Python 代码示例")

    assert decision.generate_document is True
    assert decision.resource_types == ["code"]
    assert decision.quiz_only is True


def test_router_single_resource_requests_do_not_regress() -> None:
    agent = RouterAgent()

    quiz = agent.route("给我出几道反向传播练习题")
    ppt = agent.route("给我做一个反向传播 PPT")
    mindmap = agent.route("给我一张反向传播思维导图")
    video = agent.route("帮我找几个反向传播相关视频学习")
    animation = agent.route("帮我生成一个反向传播视频脚本")

    assert quiz.resource_types == ["quiz"]
    assert ppt.resource_types == ["ppt"]
    assert mindmap.resource_types == ["mindmap"]
    assert video.resource_types == ["video"]
    assert animation.resource_types == ["animation"]


def test_router_tutor_code_question_does_not_generate_resources() -> None:
    agent = RouterAgent()

    decision = agent.route("这段代码我没看懂")

    assert decision.is_tutor_question is True
    assert decision.generate_document is False
    assert decision.resource_types == []
