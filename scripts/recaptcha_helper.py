#!/usr/bin/env python3
"""
Helper script to automatically obtain reCaptcha token for Cinema City login
Requires Selenium and a Chrome/Chromium browser
"""

def get_recaptcha_token_selenium(email: str, password: str) -> str:
    """
    Automatycznie pobierz token reCaptcha używając Selenium

    Installation:
        pip install selenium undetected-chromedriver

    Usage:
        from recaptcha_helper import get_recaptcha_token_selenium
        token = get_recaptcha_token_selenium("email@example.com", "password")
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
    except ImportError:
        print("Error: Selenium not installed")
        print("Install: pip install selenium undetected-chromedriver")
        return None

    # Enable network logging
    capabilities = DesiredCapabilities.CHROME
    capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}

    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')

    driver = webdriver.Chrome(options=options)
    recaptcha_token = None

    try:
        # Navigate to login page
        print("Opening login page...")
        driver.get("https://www.cinema-city.pl/konto#/zaloguj")

        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )

        # Fill in credentials
        print("Filling credentials...")
        driver.find_element(By.NAME, "username").send_keys(email)
        driver.find_element(By.NAME, "password").send_keys(password)

        # Start monitoring network requests
        print("Clicking login button...")

        # Click login button
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()

        # Wait a moment for the request to be made
        import time
        time.sleep(3)

        # Get network logs
        print("Analyzing network requests...")
        logs = driver.get_log('performance')

        for log in logs:
            import json
            message = json.loads(log['message'])

            # Look for the OAuth token request
            if 'Network.requestWillBeSent' in message['message']['method']:
                request_url = message['message']['params'].get('request', {}).get('url', '')

                if 'oauth/token?reCaptcha=' in request_url:
                    # Extract token from URL
                    recaptcha_token = request_url.split('reCaptcha=')[1].split('&')[0]
                    print(f"\n✓ Found reCaptcha token!")
                    break

        if not recaptcha_token:
            print("\n✗ Could not find reCaptcha token in network logs")
            print("Try manual method from references/workflows.md (sekcja Unlimited)")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")

    finally:
        driver.quit()

    return recaptcha_token


def get_site_key_from_page() -> str:
    """
    Pobierz Site Key reCaptcha ze strony Cinema City
    """
    import requests
    import re

    try:
        # Get login page
        response = requests.get("https://www.cinema-city.pl/konto")
        html = response.text

        # Look for reCaptcha site key patterns
        # Site keys typically start with "6L"
        patterns = [
            r'sitekey["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'site_key["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'data-sitekey=["\']([^"\']+)["\']',
            r'(6L[a-zA-Z0-9_-]{38,})',  # reCaptcha site key format
        ]

        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                site_key = match.group(1)
                if site_key.startswith('6L'):
                    return site_key

        return None

    except Exception as e:
        print(f"Error finding site key: {e}")
        return None


if __name__ == "__main__":
    import sys

    print("Cinema City reCaptcha Helper")
    print("=" * 50)

    # Try to find site key first
    print("\n1. Looking for reCaptcha site key...")
    site_key = get_site_key_from_page()
    if site_key:
        print(f"✓ Found site key: {site_key}")
        print(f"\nYou can use this in browser console:")
        print(f"grecaptcha.execute('{site_key}', {{action: 'login'}}).then(token => console.log(token))")
    else:
        print("✗ Could not find site key automatically")

    # Selenium method
    print("\n2. Automatic token extraction (Selenium)")
    print("This requires selenium and chromedriver installed.")

    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]

        print(f"\nAttempting to get token for: {email}")
        token = get_recaptcha_token_selenium(email, password)

        if token:
            print(f"\nreCaptcha Token: {token}")
            print(f"\nUse it like this:")
            print(f'python3 main.py login --email "{email}" --password "***" --recaptcha-token "{token}"')
        else:
            print("\nFailed to get token automatically.")
            print("Please use manual method from references/workflows.md (sekcja Unlimited)")
    else:
        print("\nUsage:")
        print("  python3 recaptcha_helper.py <email> <password>")
        print("\nOr use manual method from references/workflows.md (sekcja Unlimited)")
