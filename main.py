from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # headless=False để nhìn thấy browser
    page = browser.new_page()
    page.goto("https://www.google.com")

    # Nhập từ khóa
    page.fill("input[name='q']", "Python")
    page.press("input[name='q']", "Enter")

    # Đợi 5 giây để xem kết quả
    page.wait_for_timeout(5000)
    browser.close()
