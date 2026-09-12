# -*- coding: utf-8 -*-
"""EduAgent aApp logic.py 回归测试 — remio_sdk stub harness。

本文件在任何被测模块导入之前，向 sys.modules 注入假 remio_sdk，使
D:\\App\\remiocn\\...\\eduagent-pro\\eduagent-pro\\logic.py 能够在纯 pytest
进程内（无 remio 宿主）运行。

stub 提供的能力：
- router.route(method, path)：记录路由并原样返回 handler；
- 内存 notes store（noteId -> {title, content, collections}），create_note /
  update_note / read_note / search_notes / add_note_to_collection 全部读写它；
- 调用日志 STATE.calls：记录每次 stub 函数调用 (函数名, args, kwargs)，
  供断言「事件路径不写画像」「send_chat_message 是否被调」等；
- run_prompt 可按测试用例注入返回（模块级可变兜底：默认返回合法单题 quiz JSON）；
- create_aapp_logger 返回带 info/warn 的哑 logger；
- syscall('web_search'/'web_get') 默认无命中，让知识来源落到内置 data/kb。
"""

import importlib.util
import itertools
import json
import os
import sys
import types
from types import SimpleNamespace

import pytest

# ---- 被测 aApp 目录（可用环境变量 EDUAGENT_AAPP_LOGIC_DIR 覆盖）------------
DEFAULT_AAPP_DIR = (
    r'D:\App\remiocn\Users\B60CFB8513AF4288DF6E5A688248A005\agent\remio'
    r'\aapps-dev\eduagent-pro\eduagent-pro'
)
AAPP_DIR = os.environ.get('EDUAGENT_AAPP_LOGIC_DIR', DEFAULT_AAPP_DIR)
LOGIC_PATH = os.path.join(AAPP_DIR, 'logic.py')

PROFILE_NOTE_TITLE = 'EduAgent 学生画像'
PROFILE_BACKUP_NOTE_TITLE = '[EduAgent画像备份]'
MATERIAL_COLLECTION = 'EduAgent 学习材料'
RESOURCE_COLLECTION = 'EduAgent 学习资源'

# run_prompt 的模块级兜底输出：合法的单题 quiz JSON（出题/复习事件端点可直接消费，
# 讲义等纯文本端点也只是把它当文本使用）。
DEFAULT_RUN_PROMPT_OUTPUT = json.dumps(
    {
        'topic': 'TCP 三次握手',
        'questions': [
            {
                'type': 'input',
                'question': 'TCP 建立连接需要几次握手？',
                'options': [],
                'answer': '三次',
                'explanation': '',
            }
        ],
    },
    ensure_ascii=False,
)


class StubState:
    """内存 notes store + 调用日志 + run_prompt 注入口（模块级单例，fixture 负责重置）。"""

    def __init__(self):
        self.default_run_prompt_output = DEFAULT_RUN_PROMPT_OUTPUT
        self.notes = {}
        self.calls = []
        self.run_prompt_calls = []
        self._run_prompt_result = {}
        self.reset()

    def reset(self):
        """每个测试用例拿到干净的 store / 日志 / run_prompt 默认返回。"""
        self.notes = {}
        self.calls = []
        self.run_prompt_calls = []
        self._run_prompt_result = {'ok': True, 'output': self.default_run_prompt_output}

    # -- run_prompt 注入口 ----------------------------------------------------
    def set_run_prompt_output(self, output, ok=True):
        self._run_prompt_result = {'ok': ok, 'output': output}

    # -- 种子（直接写 store，不经过 stub 函数，因此不产生调用日志）--------------
    def seed_note(self, title, content, collections=()):
        note_id = f'seed-{len(self.notes) + 1}'
        while note_id in self.notes:
            note_id += '-x'
        self.notes[note_id] = {
            'noteId': note_id,
            'title': title,
            'content': content,
            'collections': set(collections),
        }
        return note_id

    def seed_profile(self, profile):
        """画像 note 的 title 必须是「EduAgent 学生画像」（search_notes title_filter 匹配）。

        update-or-create 语义：画像 note 全局唯一，重复种子时覆盖已有画像，
        避免同一 store 中出现两个画像 note 让 _find_profile_note_id 命中旧值。
        """
        content = json.dumps(profile, ensure_ascii=False, indent=2)
        for note in self.notes.values():
            if note['title'] == PROFILE_NOTE_TITLE:
                note['content'] = content
                return note['noteId']
        return self.seed_note(PROFILE_NOTE_TITLE, content)

    # -- 断言辅助 --------------------------------------------------------------
    def calls_by(self, name):
        return [entry for entry in self.calls if entry[0] == name]

    def find_notes(self, title):
        return [note for note in self.notes.values() if note['title'] == title]


STATE = StubState()


def _record(name, args, kwargs):
    STATE.calls.append((name, args, kwargs))


# ---- remio_sdk 各函数的 stub 实现 -------------------------------------------

def stub_create_note(title, content=''):
    _record('create_note', (title, content), {})
    note_id = f'note-{len(STATE.notes) + 1}'
    while note_id in STATE.notes:
        note_id += '-x'
    note = {'noteId': note_id, 'title': title, 'content': content, 'collections': set()}
    STATE.notes[note_id] = note
    return {'ok': True, 'data': dict(note)}


def stub_update_note(note_id, content=''):
    _record('update_note', (note_id,), {'content': content})
    note = STATE.notes.get(note_id)
    if note is None:
        return {'ok': False, 'error': f'note not found: {note_id}'}
    note['content'] = content
    return {'ok': True, 'data': dict(note)}


def stub_read_note(note_id):
    _record('read_note', (note_id,), {})
    note = STATE.notes.get(note_id)
    if note is None:
        return {'ok': False, 'error': f'note not found: {note_id}'}
    return {
        'ok': True,
        'data': {'noteId': note['noteId'], 'title': note['title'], 'content': note['content']},
    }


def stub_search_notes(params):
    _record('search_notes', (params,), {})
    params = dict(params or {})
    results = list(STATE.notes.values())

    title_filter = params.get('title_filter')
    if title_filter:
        wanted = set(title_filter)
        results = [n for n in results if n['title'] in wanted]

    query = str(params.get('query', '')).strip()
    if query:
        tokens = [t for t in query.lower().split() if t]
        if tokens:
            def _matches(note):
                haystack = (note['title'] + '\n' + note['content']).lower()
                return any(token in haystack for token in tokens)

            results = [n for n in results if _matches(n)]

    folder = params.get('folder')
    if folder:
        # stub store 中没有 remio 同步文件夹的笔记（除非显式设置 folder 字段），
        # 因此知识库 tier 默认无命中，逻辑落到内置 data/kb。
        results = [n for n in results if n.get('folder') == folder]

    collection = params.get('collection')
    if collection:
        results = [n for n in results if collection in n['collections']]

    limit = int(params.get('limit', 20) or 20)
    return {'ok': True, 'data': {'results': [dict(n) for n in results[:limit]]}}


def stub_add_note_to_collection(note_id, collection):
    _record('add_note_to_collection', (note_id, collection), {})
    note = STATE.notes.get(note_id)
    if note is None:
        return {'ok': False, 'error': f'note not found: {note_id}'}
    note['collections'].add(collection)
    return {'ok': True, 'data': {'noteId': note_id, 'collection': collection}}


def stub_send_chat_message(message):
    _record('send_chat_message', (message,), {})
    return {'ok': True, 'data': {}}


def stub_syscall(name, args=None):
    _record('syscall', (name, args), {})
    if name == 'web_search':
        return {'ok': True, 'data': {'results': []}}  # 默认无命中 → tier 落到内置库
    if name == 'web_get':
        return {'ok': True, 'data': {'markdown': ''}}
    return {'ok': False, 'error': f'unsupported syscall: {name}'}


def stub_run_prompt(prompt, **kwargs):
    _record('run_prompt', (prompt,), kwargs)
    STATE.run_prompt_calls.append({'prompt': prompt, **kwargs})
    return dict(STATE._run_prompt_result)


class StubRouter:
    """route(method, path) 记录路由并原样返回函数；handle 按 (method, path) 分发。"""

    def __init__(self):
        self.routes = []

    def route(self, method, path):
        def decorator(fn):
            self.routes.append({'method': method, 'path': path, 'handler': fn})
            return fn

        return decorator

    def handle(self, method, path, params=None):
        for route in self.routes:
            if route['method'] == method and route['path'] == path:
                return route['handler'](params or {})
        raise LookupError(f'no route registered for {method} {path}')


ROUTER = StubRouter()


def stub_create_aapp_logger(name, log_dir='', stream=''):
    class _StubLogger:
        def info(self, *args, **kwargs):
            return None

        def warn(self, *args, **kwargs):
            return None

    return _StubLogger()


def _install_fake_remio_sdk():
    """在任何 logic 导入前把假 remio_sdk 注入 sys.modules（幂等）。"""
    existing = sys.modules.get('remio_sdk')
    if existing is not None and getattr(existing, '__eduagent_stub__', False):
        return
    fake = types.ModuleType('remio_sdk')
    fake.__eduagent_stub__ = True
    fake.router = ROUTER
    fake.create_note = stub_create_note
    fake.update_note = stub_update_note
    fake.read_note = stub_read_note
    fake.search_notes = stub_search_notes
    fake.add_note_to_collection = stub_add_note_to_collection
    fake.send_chat_message = stub_send_chat_message
    fake.syscall = stub_syscall
    fake.run_prompt = stub_run_prompt
    fake.create_aapp_logger = stub_create_aapp_logger
    sys.modules['remio_sdk'] = fake


_install_fake_remio_sdk()


# ---- fixture：按唯一模块名导入被测 logic.py ----------------------------------

_module_counter = itertools.count(1)


@pytest.fixture
def logic():
    """导入被测 logic.py 并暴露 module / notes store / 调用日志 / run_prompt 注入口。

    每个测试用例：干净的 store 与调用日志、默认 run_prompt 兜底返回、
    REMIO_AAPP_DIR 指向被测目录（模块级 AAPP_DIR / KB_DATA_DIR 据此求值）。
    """
    if not os.path.isfile(LOGIC_PATH):
        pytest.skip(f'被测 logic.py 不存在: {LOGIC_PATH}')

    STATE.reset()
    old_env = {key: os.environ.get(key) for key in ('REMIO_AAPP_DIR', 'REMIO_AAPP_LOG_DIR')}
    os.environ['REMIO_AAPP_DIR'] = AAPP_DIR
    os.environ.pop('REMIO_AAPP_LOG_DIR', None)

    module_name = f'_eduagent_logic_uut_{next(_module_counter)}'
    spec = importlib.util.spec_from_file_location(module_name, LOGIC_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    try:
        yield SimpleNamespace(
            module=module,
            state=STATE,
            notes=STATE.notes,
            calls=STATE.calls,
            set_run_prompt_output=STATE.set_run_prompt_output,
        )
    finally:
        sys.modules.pop(module_name, None)
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
