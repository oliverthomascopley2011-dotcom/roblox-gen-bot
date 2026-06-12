import random
import requests
from typing import Optional


class ProxyManager:
    """
    Manages IP rotation. Each call to get_proxy() returns a different IP.
    Supports residential proxy gateways (auto-rotate) or static proxy lists.
    """

    def __init__(self, mode: str = "residential", proxy_url: str = None, proxy_list_file: str = None):
        self.mode = mode
        self.proxies = []
        self.index = 0

        if mode == "residential" and proxy_url:
            self.gateway_url = proxy_url
            self.proxies = [proxy_url]

        elif mode == "list" and proxy_list_file:
            try:
                with open(proxy_list_file, "r") as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                random.shuffle(self.proxies)
                print(f"[+] Loaded {len(self.proxies)} proxies from {proxy_list_file}")
            except FileNotFoundError:
                print(f"[!] Proxy list file {proxy_list_file} not found — using direct")
                self.proxies = []

        elif mode == "direct":
            print("[+] Running without proxy (direct connection)")
            self.proxies = []

        # Quick health check
        self._verify()
    
    def _verify(self):
        if not self.proxies:
            return
        test_url = "https://httpbin.org/ip"
        for p in self.proxies[:2]:
            try:
                r = requests.get(test_url, proxies={"http": p, "https": p}, timeout=10)
                print(f"[+] Proxy OK -> IP: {r.json().get('origin', '?')[:30]}")
            except Exception as e:
                print(f"[-] Proxy check failed: {e}")

    def get_proxy(self) -> Optional[dict]:
        if not self.proxies:
            return None
        if self.mode == "residential":
            proxy = self.proxies[0]
        else:
            proxy = self.proxies[self.index % len(self.proxies)]
            self.index += 1
        return {"http": proxy, "https": proxy}