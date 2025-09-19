import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from playwright.sync_api import sync_playwright, expect
import time
from playwright.sync_api import sync_playwright
from playwright.sync_api import expect
load_dotenv()
SSO_ID = os.getenv("SSO_ID")
PASSWORD = os.getenv("PASSWORD")
if not SSO_ID or not PASSWORD:
    raise ValueError("Thiếu SSO_ID hoặc PASSWORD trong file .env")
def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) 
        page = browser.new_page()
        page.goto("https://ramcoasean.concentrix.com")
        page.get_by_text("Concentrix Authentication", exact=True).click()
        selector = 'input#username' 
        page.wait_for_selector(selector, timeout=10000)
        page.fill(selector, SSO_ID)
        page.click('button[type="submit"]')
        page.get_by_text("Login with Password", exact=True).click()
        pw_selector = 'input#password'
        page.wait_for_selector(pw_selector, timeout=10000)
        page.fill(pw_selector, PASSWORD)
        page.click('button[type="submit"]')  
        try:
            page.wait_for_selector('input[id="KmsiCheckboxField"]', timeout=5000)
            page.check('input[id="KmsiCheckboxField"]')
            page.click('input[type="submit"]')
        except:
            pass
        from playwright.sync_api import expect
        try:
            expect(page.get_by_text("My Attendance")).to_be_visible(timeout=15000)
        except:
            pass 
        try:
            page.locator(
                "span[id^='btnhrbook1_inbtn-button'][id$='-btnInnerEl']",
                has_text="In"
            ).first.click(timeout=5000)
            print("✅ Đã click Check In (main page)")
        except:
            clicked = False
            for f in page.frames:
                try:
                    f.locator(
                        "span[id^='btnhrbook1_inbtn-button'][id$='-btnInnerEl']",
                        has_text="In"
                    ).first.click(timeout=500)
                    print("✅ Đã click Check In (iframe)")
                    clicked = True
                    break
                except:
                    continue
            if not clicked:
                try:
                    page.get_by_text("In", exact=True).first.click(timeout=500)
                    print("✅ Đã click Check In (by text)")
                except:
                    print("ℹ️ Không tìm thấy hoặc nút Check In không khả dụng")
        # time.sleep(15)
        page.wait_for_load_state("networkidle")

        page.screenshot(path="QuicklycheckNM_PR_AL.png", full_page=True)
        # page.screenshot(path="QuicklycheckNM_PR_AL.png") //backup before
        browser.close()

if __name__ == "__main__":
    run()