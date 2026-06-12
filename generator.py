import json
import random
import re
import requests
import base64
import time
from typing import Optional

from config import ROBLOX_USER_AGENTS, MIN_DELAY, MAX_DELAY


class RobloxGen:
    """
    Roblox account generator with per-request IP rotation.
    Designed for authorized security assessment of anti-automation controls.
    """

    def __init__(self, proxy_manager, captcha_solver):
        self.pm = proxy_manager
        self.cs = captcha_solver
        self.session = requests.Session()

    def _headers(self, csrf=None):
        h = {
            "User-Agent": random.choice(ROBLOX_USER_AGENTS),
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.roblox.com",
            "Referer": "https://www.roblox.com/",
        }
        if csrf:
            h["X-CSRF-TOKEN"] = csrf
        return h

    def _get_csrf(self) -> str:
        """Get CSRF token by triggering a 403 then reading the response header."""
        proxy = self.pm.get_proxy()
        r = requests.post(
            "https://auth.roblox.com/v2/signup",
            headers=self._headers(),
            json={},
            proxies=proxy,
            timeout=30
        )
        if "x-csrf-token" in r.headers:
            return r.headers["x-csrf-token"]

        # Fallback: scrape from homepage meta tag
        r2 = requests.get("https://www.roblox.com/", headers=self._headers(), proxies=proxy, timeout=30)
        m = re.search(r'<meta name="csrf-token" data-token="([^"]+)"', r2.text)
        if m:
            return m.group(1)
        return ""

    def _validate_user(self, username, birthday, csrf) -> bool:
        proxy = self.pm.get_proxy()
        r = requests.get(
            "https://auth.roblox.com/v1/usernames/validate",
            params={"birthday": birthday, "context": "Signup", "username": username},
            headers=self._headers(csrf),
            proxies=proxy,
            timeout=30
        )
        return r.status_code == 200 and r.json().get("code") == 0

    def _get_challenge_meta(self, csrf) -> dict:
        """Trigger challenge metadata from Roblox signup endpoint."""
        proxy = self.pm.get_proxy()
        test = {
            "username": "validate__check",
            "password": "TempPass123!",
            "birthday": "2000-01-01T00:00:00.000Z",
            "gender": 2,
            "isTosAgreementBoxChecked": True,
        }
        r = requests.post(
            "https://auth.roblox.com/v2/signup",
            headers=self._headers(csrf),
            json=test,
            proxies=proxy,
            timeout=30
        )
        meta_b64 = r.headers.get("rblx-challenge-metadata")
        if meta_b64:
            try:
                return json.loads(base64.b64decode(meta_b64))
            except:
                pass
        return {}

    def create(self, username: str = None, password: str = None) -> dict:
        """Create one Roblox account. Returns account dict or error."""
        if not username:
            username = f"Test{random.randint(10000, 99999)}{random.randint(100, 999)}"
        if not password:
            password = f"GenPass{random.randint(1000, 9999)}!"

        birthday = f"{random.randint(1995, 2005)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}T00:00:00.000Z"
        gender = random.choice([1, 2])

        print(f"\n[*] Creating: {username}")

        # Step 1: Get CSRF
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        csrf = self._get_csrf()
        if not csrf:
            return {"success": False, "error": "No CSRF token"}

        # Step 2: Validate username
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        if not self._validate_user(username, birthday, csrf):
            return {"success": False, "error": "Username taken or invalid"}

        # Step 3: Get challenge metadata
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        meta = self._get_challenge_meta(csrf)

        # Step 4: Solve captcha if needed
        captcha_token = ""
        blob = meta.get("dataExchangeBlob", "")
        if blob:
            captcha_token = self.cs.solve(blob)

        # Step 5: Submit signup
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        proxy = self.pm.get_proxy()

        payload = {
            "username": username,
            "password": password,
            "birthday": birthday,
            "gender": gender,
            "isTosAgreementBoxChecked": True,
        }

        if captcha_token and meta:
            payload["captchaToken"] = captcha_token
            payload["captchaProvider"] = "PROVIDER_ARKOSE_LABS"
            payload["unifiedCaptchaId"] = meta.get("unifiedCaptchaId", "")
            payload["dataExchangeBlob"] = blob

        headers = self._headers(csrf)
        headers["Content-Type"] = "application/json;charset=UTF-8"

        r = requests.post(
            "https://auth.roblox.com/v2/signup",
            headers=headers,
            json=payload,
            proxies=proxy,
            timeout=30
        )

        if r.status_code == 200:
            data = r.json()
            uid = data.get("userId")
            return {
                "success": True,
                "username": username,
                "password": password,
                "user_id": uid,
                "cookie": r.cookies.get(".ROBLOSECURITY", "")
            }

        try:
            err = r.json().get("errors", [{}])[0].get("message", str(r.status_code))
        except:
            err = f"HTTP {r.status_code}"
        return {"success": False, "error": err}