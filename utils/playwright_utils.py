# utils/playwright_utils.py
from playwright.async_api import async_playwright, TimeoutError
from utils.logger import logger
import asyncio

DASHBOARD_URL = "https://splunk-apm-url.com/dashboard"
SCREENSHOT_PATH = "/tmp/splunk_apm_dashboard.png"

async def capture_screenshot(retries=3):
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(DASHBOARD_URL, timeout=60000)
                await page.wait_for_timeout(5000)
                await page.screenshot(path=SCREENSHOT_PATH)
                await browser.close()
                logger.info("Screenshot captured successfully.")
                return SCREENSHOT_PATH
        except TimeoutError as te:
            logger.warning(f"Timeout on attempt {attempt+1}: {te}")
        except Exception as e:
            logger.error(f"Playwright error on attempt {attempt+1}: {e}")
        await asyncio.sleep(2)
    logger.error("All screenshot attempts failed.")
    return None
