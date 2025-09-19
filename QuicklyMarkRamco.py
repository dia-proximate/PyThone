#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import datetime
import time
import traceback
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ---------------------------
# Cấu hình cơ bản / env
# ---------------------------
load_dotenv()

SSO_ID = os.getenv("SSO_ID")
PASSWORD = os.getenv("PASSWORD")
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("1", "true", "yes")
LOG_DIR = os.getenv("LOG_DIR", os.path.join(os.path.dirname(__file__), "logs"))
STATE_FILE = os.path.join(LOG_DIR, "state.json")
LOG_FILE = os.path.join(LOG_DIR, "ramco_checkin.log")
SCREENSHOT_DIR = os.path.join(LOG_DIR, "screenshots")

# Kiểm tra env bắt buộc
if not SSO_ID or not PASSWORD:
    raise ValueError("Thiếu SSO_ID hoặc PASSWORD trong file .env")

# Đảm bảo stdout hỗ trợ UTF-8 để tránh UnicodeEncodeError trên Windows console
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    # Python cũ / môi trường không hỗ trợ reconfigure thì bỏ qua
    pass

# ---------------------------
# Logging
# ---------------------------
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

logger = logging.getLogger("ramco_checkin")
logger.setLevel(logging.INFO)

fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S")

# Console handler
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(fmt)
logger.addHandler(ch)

# File handler (UTF-8)
fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
fh.setFormatter(fmt)
logger.addHandler(fh)

# ---------------------------
# State (kiểm tra đã checkin hôm nay chưa)
# ---------------------------
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)

def already_checked_today() -> bool:
    state = load_state()
    last = state.get("last_checkin_date")
    today = datetime.date.today().isoformat()
    return last == today

def mark_checked_today():
    state = load_state()
    state["last_checkin_date"] = datetime.date.today().isoformat()
    save_state(state)

# ---------------------------
# Helpers Playwright
# ---------------------------
def safe_click_locator(locator, desc: str, click_timeout=8000, wait_visible_timeout=10000) -> bool:
    """
    Thử đợi visible rồi click. Trả về True nếu click thành công.
    """
    try:
        # Đợi element visible
        locator.first.wait_for(state="visible", timeout=wait_visible_timeout)
        # Click (nếu cần có option thêm có thể đặt ở đây)
        locator.first.click(timeout=click_timeout)
        logger.info(f"✅ Clicked: {desc}")
        return True
    except PlaywrightTimeoutError:
        logger.debug(f"Timeout khi cố click: {desc}")
        return False
    except Exception as e:
        logger.debug(f"Exception khi click {desc}: {e}")
        return False

def find_and_click_checkin(page) -> bool:
    """
    Luồng tìm và click nút 'In' theo thứ tự:
    1) selector cụ thể trên main page
    2) tìm trong các iframe
    3) fallback get_by_text("In")
    Mỗi bước có timeout & retry nhẹ.
    """
    # tăng default timeout cho page operations nếu cần
    page.set_default_timeout(15000)

    # 1) selector cụ thể (theo cấu trúc trước đó)
    css_selector = "span[id^='btnhrbook1_inbtn-button'][id$='-btnInnerEl']"
    try:
        loc = page.locator(css_selector, has_text="In")
        if safe_click_locator(loc, "Check In (main selector)"):
            return True
    except Exception:
        logger.debug("Không tìm thấy main selector hoặc lỗi khi click main selector")

    # 2) tìm trong iframe(s)
    try:
        frames = page.frames
        for idx, f in enumerate(frames):
            try:
                locf = f.locator(css_selector, has_text="In")
                if safe_click_locator(locf, f"Check In (iframe {idx})", click_timeout=2000, wait_visible_timeout=3000):
                    return True
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"Lỗi khi duyệt frames: {e}")

    # 3) fallback: tìm theo text
    try:
        text_loc = page.get_by_text("In", exact=True)
        if safe_click_locator(text_loc, "Check In (by text)", click_timeout=4000, wait_visible_timeout=5000):
            return True
    except Exception:
        logger.debug("Fallback get_by_text không thành công")

    return False

# ---------------------------
# Main workflow
# ---------------------------
def run():
    logger.info("Bắt đầu quy trình check-in Ramco")
    if already_checked_today():
        logger.info("Đã chấm công hôm nay. Skip.")
        return 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=HEADLESS)
            context = browser.new_context()
            page = context.new_page()

            # vào trang
            page.goto("https://ramcoasean.concentrix.com", timeout=30000)
            logger.info("Đã tải trang ramcoasean")

            # các bước login cơ bản (giữ nguyên flow bạn có)
            try:
                page.get_by_text("Concentrix Authentication", exact=True).click(timeout=8000)
            except Exception:
                logger.debug("Không click được Concentrix Authentication (có thể không hiện)")

            # login form
            selector_username = 'input#username'
            page.wait_for_selector(selector_username, timeout=15000)
            page.fill(selector_username, SSO_ID)
            page.click('button[type="submit"]')

            # login with password path
            try:
                page.get_by_text("Login with Password", exact=True).click(timeout=8000)
            except Exception:
                logger.debug("Không thấy 'Login with Password'")

            pw_selector = 'input#password'
            page.wait_for_selector(pw_selector, timeout=15000)
            page.fill(pw_selector, PASSWORD)
            page.click('button[type="submit"]')

            # optional: KMSI handling
            try:
                page.wait_for_selector('input[id="KmsiCheckboxField"]', timeout=5000)
                page.check('input[id="KmsiCheckboxField"]')
                page.click('input[type="submit"]')
            except Exception:
                logger.debug("Không thấy Kmsi checkbox (bỏ qua nếu không có)")

            # chờ trang Attendance load (dùng expect nếu muốn, ở đây tối giản wait)
            try:
                page.wait_for_selector("text=My Attendance", timeout=20000)
            except Exception:
                logger.debug("Không thấy text 'My Attendance' sau login. Tiếp tục thử tìm nút In.")

            # Tăng cơ chế thử: nhiều lần cố click với backoff
            clicked = False
            attempts = 3
            for attempt in range(1, attempts + 1):
                logger.info(f"Cố click Check In - lần {attempt}/{attempts}")
                if find_and_click_checkin(page):
                    clicked = True
                    break
                sleep_sec = 2 * attempt
                logger.debug(f"Không thành công, chờ {sleep_sec}s rồi thử lại")
                time.sleep(sleep_sec)

            if clicked:
                # chờ network idle, chụp màn hình, ghi nhật ký
                try:
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(SCREENSHOT_DIR, f"checkin_{ts}.png")
                page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"Đã check-in. Screenshot: {screenshot_path}")

                # đánh dấu đã check hôm nay
                mark_checked_today()
                logger.info("Đã ghi trạng thái: checked today")
            else:
                msg = "ℹ️ Không tìm thấy hoặc nút Check In không khả dụng (có thể đã chấm công rồi)"
                logger.info(msg)
                # lưu screenshot để debug
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(SCREENSHOT_DIR, f"no_checkin_{ts}.png")
                try:
                    page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"Screenshot debug: {screenshot_path}")
                except Exception:
                    logger.debug("Không thể chụp màn hình debug")

            # dọn dẹp
            try:
                context.close()
            except Exception:
                pass
            browser.close()
        return 0
    except Exception as e:
        logger.error("Lỗi trong quá trình chạy script:")
        logger.error(traceback.format_exc())
        return 2

if __name__ == "__main__":
    exit_code = run()
    sys.exit(exit_code)
