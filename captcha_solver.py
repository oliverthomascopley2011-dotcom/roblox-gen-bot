import json
import requests
import time
from typing import Optional


class CaptchaSolver:
    """Handles Funcaptcha solving for Roblox signup."""

    def __init__(self, service: str = "manual", api_key: str = ""):
        self.service = service
        self.api_key = api_key

    def solve(self, data_exchange_blob: str) -> Optional[str]:
        site_url = "https://www.roblox.com"
        pkey = "A2A14B1D-1AF3-C791-9BBC-EE33CC7A0A6F"

        if self.service == "manual":
            return self._manual(data_exchange_blob, site_url, pkey)
        elif self.service == "capsolver":
            return self._capsolver(data_exchange_blob, site_url, pkey)
        elif self.service == "2captcha":
            return self._2captcha(data_exchange_blob, site_url, pkey)
        else:
            return None

    def _manual(self, blob, site_url, pkey):
        print(f"\n[!] MANUAL CAPTCHA REQUIRED")
        print(f"[!] Solve at: https://roblox-api.arkoselabs.com/fc/gc/?blob={blob}")
        print(f"[!] Type the token in Discord when prompted by the bot")
        return None  # Token will be provided via Discord command

    def _capsolver(self, blob, site_url, pkey):
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "FunCaptchaTaskProxyless",
                "websiteURL": site_url,
                "websitePublicKey": pkey,
                "data": json.dumps({"blob": blob})
            }
        }
        r = requests.post("https://api.capsolver.com/createTask", json=payload)
        task_id = r.json().get("taskId")
        if not task_id:
            return None
        for _ in range(60):
            time.sleep(2)
            r = requests.post("https://api.capsolver.com/getTaskResult", json={
                "clientKey": self.api_key, "taskId": task_id
            })
            result = r.json()
            if result.get("status") == "ready":
                return result["solution"]["token"]
            if result.get("status") == "failed":
                return None
        return None

    def _2captcha(self, blob, site_url, pkey):
        payload = {
            "key": self.api_key, "method": "funcaptcha",
            "publickey": pkey, "pageurl": site_url,
            "surl": "https://roblox-api.arkoselabs.com", "json": 1
        }
        r = requests.post("https://2captcha.com/in.php", data=payload)
        captcha_id = r.json().get("request")
        if not captcha_id:
            return None
        for _ in range(60):
            time.sleep(5)
            r = requests.get(f"https://2captcha.com/res.php?key={self.api_key}&action=get&id={captcha_id}&json=1")
            if r.json().get("status") == 1:
                return r.json()["request"]
        return None