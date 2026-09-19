import playwright
import os

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    # Launch a real browser (Chromium)
    try:
        browser = p.chromium.launch(headless=True)
    except playwright._impl._errors.Error as e:
        print("Chrome headless client was not installed. Installing now... (running `playwright install`)")
        os.system("playwright install")
        browser = p.chromium.launch(headless=True)

    page = browser.new_page()
    
    # Navigate to the target site
    page.goto('https://example.com')
    
    # Wait for the network to idle (allows JS security tokens to load)
    page.wait_for_load_state('networkidle')
    
    # Extract the fully rendered HTML
    html_content = page.content()
    print(html_content)
    
    browser.close()
