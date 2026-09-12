# -*- coding: utf-8 -*-
"""EduAgent aApp logic.py 回归测试（remio_sdk stub harness）。

按 D6 验收清单钉死 10 组新机制：
1. SRS 间隔公式 / 到期列表 / 最旧优先 / 旧画像无 iv 推导
2. _add_recent_mistakes 错题沉淀（新的在前 / 同题 n+1 提前 / 上限 5 / 空题干跳过 / 走 note 存取）
3. handle_review_quiz 原题重练 / 现场生成 / 间隔期文案 / 无未掌握文案
4. handle_event 到期推送 / 间隔期不打扰 / 非画像事件忽略 / 绝不写画像 note
5. _pick_material_segments 分段命中（原序拼接 / 段边界截断 / 无命中 None）
6. 课程路由：画像「当前课程」驱动 _search_builtin_kb 扫描目录
7. handle_home 组件序列（当前课程行 / 课程切换 / 每日复习自测 / 最近资源重学）
8. handle_dashboard 有数据 / 空画像引导
9. handle_export 导出 note 的标题与章节 / 二次调用走 update_note
10. handle_generate_document 尾部「顺手复习」提醒（有到期 / 无到期）
"""

import datetime
import json
import os

import pytest

TODAY = datetime.date.today()
RESOURCE_COLLECTION = 'EduAgent 学习资源'
MATERIAL_COLLECTION = 'EduAgent 学习材料'


# ---- 展示层辅助 -------------------------------------------------------------


def _comp_text(comp):
    """把单个组件压平成文本（含 action 的 path 与 params），便于子串断言。"""
    if not isinstance(comp, dict):
        return str(comp)
    parts = [str(comp.get(key, '')) for key in ('text', 'title', 'content', 'subtitle', 'label')]
    action = comp.get('action')
    if isinstance(action, dict):
        parts.append(str(action.get('path', '')))
        parts.append(json.dumps(action.get('params', {}), ensure_ascii=False))
    return '\n'.join(part for part in parts if part)


def render(components):
    return '\n'.join(_comp_text(comp) for comp in components)


def buttons_of(components):
    return [comp for comp in components if isinstance(comp, dict) and comp.get('kind') == 'button']


def find_button(components, label):
    hits = [b for b in buttons_of(components) if b.get('label') == label]
    return hits[0] if hits else None


# ---- 画像条目构造辅助 --------------------------------------------------------


def due_entry(topic, n=1, days_ago=1, iv=1):
    """已到期的薄弱点：ts + iv 天 <= 今天（昨天记错、间隔 1 天 → 今天到期）。"""
    return {
        't': topic,
        'ts': (TODAY - datetime.timedelta(days=days_ago)).isoformat(),
        'n': n,
        'm': False,
        'iv': iv,
    }


def interval_entry(topic, n=1, iv=3):
    """间隔期内的薄弱点：ts=今天 → 明天才到期，今天不应打扰。"""
    return {'t': topic, 'ts': TODAY.isoformat(), 'n': n, 'm': False, 'iv': iv}


PROFILE_EVENT = {
    'content_type': 'note',
    'operation': 'modified',
    'payload': {'title': 'EduAgent 学生画像'},
}


# ---- 机制 1：SRS 间隔公式 / 到期轮转 ----------------------------------------


def test_srs_interval_formula_and_due_rotation(logic):
    """机制1：_srs_interval = min(2^(n-1), 30)；到期列表只含未掌握且今天>=ts+iv 的条目按 ts 升序；
    _pick_due_weak_point 取最旧；旧画像无 iv 字段时按 n 推导（n=1 → 1 天）。"""
    m = logic.module

    # 间隔公式：1/2/4/8/16/…，封顶 30
    assert m._srs_interval(1) == 1
    assert m._srs_interval(2) == 2
    assert m._srs_interval(3) == 4
    assert m._srs_interval(4) == 8
    assert m._srs_interval(5) == 16
    assert m._srs_interval(6) == 30
    assert m._srs_interval(10) == 30

    profile = {
        'weak_points': [
            interval_entry('未到期项', iv=2),
            due_entry('到期旧题A', days_ago=3, iv=2),
            due_entry('到期旧题B', days_ago=5, iv=2),
            {**due_entry('已掌握项', days_ago=9, iv=2), 'm': True},
        ]
    }
    due = m._list_due_weak_points(profile)
    assert [e['t'] for e in due] == ['到期旧题B', '到期旧题A']  # 按 ts 升序，排除未到期/已掌握
    assert m._pick_due_weak_point(profile)['t'] == '到期旧题B'  # 取最旧
    assert m._pick_due_weak_point({'weak_points': []}) is None

    # 旧画像无 iv：n=1 → 间隔 1 天 → 昨天 + 1 = 今天 → 今天即到期
    old_profile = {'weak_points': [{'t': '旧画像项', 'ts': (TODAY - datetime.timedelta(days=1)).isoformat(), 'n': 1, 'm': False}]}
    due_old = m._list_due_weak_points(old_profile)
    assert [e['t'] for e in due_old] == ['旧画像项']
    assert due_old[0]['iv'] == 1


# ---- 机制 2：错题沉淀 -------------------------------------------------------


def test_add_recent_mistakes_persists_via_notes(logic):
    """机制2：_add_recent_mistakes 写画像 recent_mistakes（load→save 走 note 存取）；
    新的在前、同题再错 n+1 并提前、上限 5 条、空题干跳过。"""
    m = logic.module
    logic.state.seed_profile(
        {'当前课程': '计算机网络', 'recent_mistakes': [{'q': '旧题', 'a': '旧答', 't': 'UDP', 'n': 1}]}
    )

    m._add_recent_mistakes([('新题A', '答A'), ('新题B', '答B')], 'TCP')
    profile = m._load_profile()
    assert [x['q'] for x in profile['recent_mistakes']] == ['新题B', '新题A', '旧题']

    # 同题再错：n+1 且提到最前
    m._add_recent_mistakes([('旧题', '旧答2')], 'UDP')
    profile = m._load_profile()
    assert profile['recent_mistakes'][0]['q'] == '旧题'
    assert profile['recent_mistakes'][0]['n'] == 2

    # 上限 5 条
    for i in range(6):
        m._add_recent_mistakes([(f'超量题{i}', 'x')], 'T')
    profile = m._load_profile()
    assert len(profile['recent_mistakes']) == m.SRS_MAX_RECENT_MISTAKES == 5

    # 空题干跳过
    m._add_recent_mistakes([('   ', 'y'), ('', 'z')], 'T')
    profile = m._load_profile()
    assert all(x['q'].strip() for x in profile['recent_mistakes'])

    # 写入确实走 note 存取（update_note 被调用）
    assert logic.state.calls_by('update_note')


# ---- 机制 3：handle_review_quiz 四分支 --------------------------------------


def test_review_quiz_replays_recent_mistakes(logic):
    """机制3a：due 主题在 recent_mistakes 有原题 → 卡片含「原题重练」与原题题干，
    不触发 run_prompt 重新生成，提交按钮指向 /grade_quiz_ui。"""
    m = logic.module
    logic.state.seed_profile(
        {
            'weak_points': [due_entry('TCP 三次握手')],
            'recent_mistakes': [{'q': 'TCP 三次握手的第一步是什么？', 'a': 'SYN', 't': 'TCP 三次握手', 'n': 1}],
        }
    )
    logic.state.set_run_prompt_output('不应被调用', ok=False)

    result = m.handle_review_quiz({})
    text = render(result['components'])
    assert '原题重练' in text
    assert 'TCP 三次握手的第一步是什么？' in text
    assert not logic.state.run_prompt_calls  # 原题重练路径不走 LLM

    submit = find_button(result['components'], '提交并解析')
    assert submit is not None
    assert submit['action']['path'] == '/grade_quiz_ui'
    assert 'TCP 三次握手' in submit['action']['params']['payload']


def test_review_quiz_falls_back_to_fresh_generation(logic):
    """机制3b：due 主题无原题 → 走 run_prompt 现场重新生成练习题。"""
    m = logic.module
    logic.state.seed_profile({'weak_points': [due_entry('动态规划')]})

    result = m.handle_review_quiz({})
    text = render(result['components'])
    assert '练习题 · 动态规划' in text
    assert logic.state.run_prompt_calls  # 确实调用了 run_prompt 重新生成


def test_review_quiz_interval_and_mastered_messages(logic):
    """机制3c/3d：全部在间隔期 → 文案含「间隔期」并提示最早复习日；
    无未掌握 → 文案含「已全部掌握或暂无记录」。"""
    m = logic.module

    logic.state.seed_profile({'weak_points': [interval_entry('UDP', iv=3)]})
    text = render(m.handle_review_quiz({})['components'])
    assert '间隔期' in text
    assert '最早' in text

    logic.state.reset()
    logic.state.seed_profile({'weak_points': []})
    text = render(m.handle_review_quiz({})['components'])
    assert '已全部掌握或暂无记录' in text


# ---- 机制 4：handle_event ---------------------------------------------------


def test_event_pushes_review_card_and_never_writes_profile(logic):
    """机制4a：画像 note 被修改且有到期薄弱点 → 返回 topic、send_chat_message 推一次
    可作答卡片；事件路径绝不调用 create_note/update_note 写画像。"""
    m = logic.module
    logic.state.seed_profile({'weak_points': [due_entry('TCP 三次握手')]})

    result = m.handle_event(dict(PROFILE_EVENT))
    assert result['handled'] is True
    assert result['topic'] == 'TCP 三次握手'
    assert result['format'] == 'card'

    msgs = logic.state.calls_by('send_chat_message')
    assert len(msgs) == 1
    payload = msgs[0][1][0]
    assert isinstance(payload, dict) and 'components' in payload
    card_text = render(payload['components'])
    assert '复习自测 · TCP 三次握手' in card_text
    submit = find_button(payload['components'], '提交答案')
    assert submit is not None and submit['action']['path'] == '/grade_quiz_ui'

    writers = [c for c in logic.state.calls if c[0] in ('create_note', 'update_note')]
    assert not writers  # 事件路径只读画像，绝不落盘


def test_event_defers_in_interval_and_ignores_non_profile(logic):
    """机制4b/4c：无到期（间隔期）→ handled 且无 topic 键、不 send_chat_message；
    非画像事件 → {'handled': False}。"""
    m = logic.module
    logic.state.seed_profile({'weak_points': [interval_entry('UDP', iv=3)]})

    result = m.handle_event(dict(PROFILE_EVENT))
    assert result['handled'] is True
    assert result.get('topic') is None
    assert not logic.state.calls_by('send_chat_message')

    # 标题不含画像短语
    other = dict(PROFILE_EVENT, payload={'title': '购物清单'})
    assert m.handle_event(other).get('handled') is False
    # content_type 不是 note
    doc = dict(PROFILE_EVENT, content_type='doc')
    assert m.handle_event(doc).get('handled') is False
    assert not logic.state.calls_by('send_chat_message')


# ---- 机制 5：材料分段命中 ----------------------------------------------------


def test_pick_material_segments_scoring_and_truncation(logic):
    """机制5：_pick_material_segments 按 '\\n\\n' 切段计分，命中段按原序拼接，
    超长截到段边界，无命中返回 None。"""
    m = logic.module
    body = '开头无关注。\n\nTCP 三次握手由 SYN 开始。\n\n无关段落。\n\n三次握手完成连接建立，随后挥手断开。'

    picked = m._pick_material_segments(body, '三次握手')
    assert picked is not None
    assert 'SYN' in picked and '挥手断开' in picked
    assert '开头无关注' not in picked and '无关段落' not in picked
    assert picked.index('SYN') < picked.index('挥手断开')  # 原序
    assert picked == 'TCP 三次握手由 SYN 开始。\n\n三次握手完成连接建立，随后挥手断开。'

    # 无命中段落 → None
    assert m._pick_material_segments(body, '量子纠缠叠加态') is None

    # 超长截断到段边界：第一命中段必保留，其后超长段整段截掉
    long1 = '甲三次握手' + '乙' * 50
    long2 = '丙三次握手' + '丁' * 50
    body2 = long1 + '\n\n' + long2
    out = m._pick_material_segments(body2, '三次握手', max_chars=len(long1) + 2 + 5)
    assert out == long1
    # 预算充足时两段完整按原序拼接
    out_full = m._pick_material_segments(body2, '三次握手', max_chars=10000)
    assert out_full == long1 + '\n\n' + long2


# ---- 机制 6：课程路由 -------------------------------------------------------


def test_course_routes_builtin_kb_by_profile(logic):
    """机制6：_current_course 默认「计算机网络」、随画像切换；
    _search_builtin_kb 只扫画像课程对应的 data/kb 子目录。"""
    m = logic.module
    kb_net = os.path.join(str(m.KB_DATA_DIR), '计算机网络知识库')
    kb_algo = os.path.join(str(m.KB_DATA_DIR), '算法设计与分析')
    if not (os.path.isdir(kb_net) and os.path.isdir(kb_algo)):
        pytest.skip('内置知识库目录 data/kb 缺失')

    assert m._current_course({}) == '计算机网络'
    assert m._current_course({'当前课程': '算法设计与分析'}) == '算法设计与分析'
    assert m._current_course({'当前课程': '不存在的课程'}) == '计算机网络'  # 非法值回落默认

    # 当前课程 = 算法设计与分析：搜「动态规划」只命中算法子目录，搜「三次握手」无命中
    logic.state.seed_profile({'当前课程': '算法设计与分析'})
    algo_hits = m._search_builtin_kb('动态规划')
    assert algo_hits, '算法课程下应命中动态规划'
    assert all('算法设计与分析' in h['path'] for h in algo_hits)
    assert m._search_builtin_kb('三次握手') == []

    # 切回计算机网络：搜「三次握手」命中且都在计算机网络知识库子目录
    logic.state.seed_profile({'当前课程': '计算机网络'})
    net_hits = m._search_builtin_kb('三次握手')
    assert net_hits, '计算机网络课程下应命中三次握手'
    assert all('计算机网络知识库' in h['path'] for h in net_hits)


# ---- 机制 7：handle_home 组件序列 -------------------------------------------


def test_home_components_course_and_resources(logic):
    """机制7：首页含当前课程行、课程切换按钮（→/build_profile_ui 带 course）、
    「🔁 每日复习自测」按钮、最近生成资源的「重学」按钮（→/plan_learning_ui 带 topic）。"""
    m = logic.module
    logic.state.seed_profile({'专业': '计算机科学', '年级': '大三'})
    logic.state.seed_note(
        '[EduAgent资源] 讲义·TCP 三次握手', '讲义正文', collections=[RESOURCE_COLLECTION]
    )

    components = m.handle_home({})['components']
    text = render(components)
    assert '📚 当前课程：计算机网络' in text

    switch = find_button(components, '切换到 算法设计与分析')
    assert switch is not None
    assert switch['action']['path'] == '/build_profile_ui'
    assert switch['action']['params'].get('course') == '算法设计与分析'
    assert find_button(components, '✅ 已在学 计算机网络') is not None

    review = find_button(components, '🔁 每日复习自测')
    assert review is not None and review['action']['path'] == '/review_quiz_ui'

    relearn = find_button(components, '🔄 重学 TCP 三次握手')
    assert relearn is not None
    assert relearn['action']['path'] == '/plan_learning_ui'
    assert relearn['action']['params'].get('topic') == 'TCP 三次握手'


# ---- 机制 8：handle_dashboard ----------------------------------------------


def test_dashboard_with_data_and_empty_guide(logic):
    """机制8：有数据时含「学习仪表盘」标题与薄弱点条目（到期/间隔期状态、到期项带复习入口）；
    空画像时仍含标题与引导文案。"""
    m = logic.module
    logic.state.seed_profile(
        {
            'weak_points': [
                due_entry('TCP 三次握手'),
                interval_entry('UDP', iv=3),
                {**due_entry('ARP', days_ago=2), 'm': True},
            ]
        }
    )

    components = m.handle_dashboard({})['components']
    assert '学习仪表盘' in render(components)
    items = [it for comp in components if comp.get('kind') == 'list' for it in comp['items']]
    by_title = {it['title']: it for it in items}
    assert {'TCP 三次握手', 'UDP', 'ARP'} <= set(by_title)
    assert '🔴 待复习' in by_title['TCP 三次握手']['description']
    assert by_title['TCP 三次握手']['actions'][0]['path'] == '/review_quiz_ui'
    assert '⏳ 间隔期' in by_title['UDP']['description']
    assert '✅ 已掌握' in by_title['ARP']['description']

    # 空画像：引导文案分支（标题仍出现；空分支不含「薄弱点」条目属正常）
    logic.state.reset()
    empty = m.handle_dashboard({})['components']
    assert '学习仪表盘' in render(empty)
    assert not [comp for comp in empty if comp.get('kind') == 'list']


# ---- 机制 9：handle_export --------------------------------------------------


def test_export_creates_then_updates_note(logic):
    """机制9：导出创建标题「[EduAgent导出] 学习档案 {今天}」的 note（标题不含「学生画像」），
    正文含 学习画像/薄弱点/生成资源清单 三节；二次调用走 update_note 不新建。"""
    m = logic.module
    logic.state.seed_profile({'专业': '软件工程', 'weak_points': [due_entry('TCP 三次握手')]})
    logic.state.seed_note(
        '[EduAgent资源] 讲义·TCP 三次握手', '讲义正文', collections=[RESOURCE_COLLECTION]
    )
    expected_title = f'[EduAgent导出] 学习档案 {TODAY.isoformat()}'

    m.handle_export({})
    created = logic.state.calls_by('create_note')
    assert len(created) == 1
    title, content = created[0][1][0], created[0][1][1]
    assert title == expected_title
    assert '学生画像' not in title  # 避开画像事件触发词
    for section in ('## 学习画像', '## 薄弱点', '## 生成资源清单'):
        assert section in content
    assert 'TCP 三次握手' in content  # 薄弱点表
    assert '[EduAgent资源] 讲义·TCP 三次握手' in content  # 资源清单

    # 二次导出：update-or-create，不新建
    m.handle_export({})
    assert len(logic.state.calls_by('create_note')) == 1
    assert logic.state.calls_by('update_note')
    assert len(logic.state.find_notes(expected_title)) == 1


# ---- 机制 10：生成端点尾部「顺手复习」提醒 -----------------------------------


def test_generate_document_review_nudge(logic):
    """机制10：handle_generate_document 在画像含到期薄弱点时 components 尾部出现
    「顺手复习」按钮（→/review_quiz_ui）；无到期时无此按钮。"""
    m = logic.module
    logic.state.seed_profile({'weak_points': [due_entry('TCP 三次握手')]})
    logic.state.set_run_prompt_output('这是一份 TCP 三次握手讲义正文。')

    components = m.handle_generate_document({'topic': 'TCP 三次握手'})['components']
    assert '个性化讲义' in render(components)
    assert components[-1].get('label') == '🔁 顺手复习'  # 尾部
    assert components[-1]['action']['path'] == '/review_quiz_ui'
    assert '薄弱点到期' in render(components)

    # 无到期：不追加提醒
    logic.state.reset()
    logic.state.seed_profile({'weak_points': [interval_entry('UDP', iv=3)]})
    components = m.handle_generate_document({'topic': 'TCP 三次握手'})['components']
    assert not [c for c in components if c.get('label') == '🔁 顺手复习']
