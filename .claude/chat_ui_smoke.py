from pathlib import Path
import os

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
USERNAME = "qa_user_20260418"
PASSWORD = "testpass123"
DISPLAY_NAME = "联调用户"
CHROMIUM_EXECUTABLE = (
    Path(os.path.expanduser("~"))
    / "AppData"
    / "Local"
    / "ms-playwright"
    / "chromium-1208"
    / "chrome-win64"
    / "chrome.exe"
)


def fill_if_visible(page, selectors, value):
    for selector in selectors:
        locator = page.locator(selector)
        if locator.count() > 0 and locator.first.is_visible():
            locator.first.fill(value)
            return True
    return False


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=str(CHROMIUM_EXECUTABLE))
    page = browser.new_page()
    logs = []
    errors = []

    page.on("console", lambda msg: logs.append(f"console[{msg.type}]: {msg.text}"))
    page.on("pageerror", lambda exc: errors.append(f"pageerror: {exc}"))

    page.goto(BASE_URL, wait_until="networkidle")

    register_visible = page.get_by_role("button", name="注册").count() > 0
    login_visible = page.get_by_role("button", name="登录").count() > 0

    if register_visible or login_visible:
        if page.get_by_role("button", name="注册").count() > 0:
            page.get_by_role("button", name="注册").click()
            page.wait_for_load_state("networkidle")

        filled_username = fill_if_visible(page, [
            'input[name="username"]',
            'input[placeholder*="用户名"]',
            'input[type="text"]',
        ], USERNAME)
        filled_password = fill_if_visible(page, [
            'input[name="password"]',
            'input[placeholder*="密码"]',
            'input[type="password"]',
        ], PASSWORD)
        fill_if_visible(page, [
            'input[name="displayName"]',
            'input[name="display_name"]',
            'input[placeholder*="昵称"]',
            'input[placeholder*="显示"]',
        ], DISPLAY_NAME)

        if not (filled_username and filled_password):
            raise RuntimeError("未找到注册/登录表单输入框")

        submit = page.get_by_role("button", name="创建账号")
        if submit.count() == 0:
            submit = page.get_by_role("button", name="注册")
        if submit.count() == 0:
            submit = page.get_by_role("button", name="登录")
        submit.first.click()
        page.wait_for_load_state("networkidle")

    page.goto(f"{BASE_URL}/chat/1", wait_until="networkidle")

    textarea = page.locator("textarea")
    textarea.wait_for(state="visible", timeout=15000)
    textarea.fill("请帮我概述机器学习的基本概念，并给我一条入门建议。")
    page.get_by_role("button", name="发送").click()

    page.wait_for_timeout(5000)
    page.wait_for_load_state("networkidle")

    current_url = page.url
    message_count = page.locator("text=请帮我概述机器学习的基本概念，并给我一条入门建议。\n").count()
    has_profile_link = page.get_by_role("link", name="查看学习画像").count() > 0
    has_sidebar_title = page.locator("text=最近会话").count() > 0

    page.get_by_role("link", name="查看学习画像").last.click()
    page.wait_for_timeout(2000)
    page.wait_for_load_state("networkidle")

    profile_url = page.url
    profile_title_visible = page.locator("text=学习画像").count() > 0

    print("RESULT current_url=", current_url)
    print("RESULT message_count=", message_count)
    print("RESULT has_profile_link=", has_profile_link)
    print("RESULT has_sidebar_title=", has_sidebar_title)
    print("RESULT profile_url=", profile_url)
    print("RESULT profile_title_visible=", profile_title_visible)

    if logs:
        print("LOGS_START")
        for line in logs:
            print(line)
        print("LOGS_END")

    if errors:
        print("ERRORS_START")
        for line in errors:
            print(line)
        print("ERRORS_END")

    browser.close()
