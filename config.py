import os
from dotenv import load_dotenv

load_dotenv()

# ===== DISCORD SETTINGS =====
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0"))

# ===== PROXY CONFIGURATION =====
# Mode: "residential" (gateway that rotates automatically per request)
#       "list"       (static proxy list, rotates round-robin)
#       "direct"     (no proxy — for testing only, will get rate limited fast)
PROXY_MODE = os.getenv("PROXY_MODE", "residential")

# Residential proxy gateway (BrightData, Smartproxy, Oxylabs, Webshare, etc.)
PROXY_URL = os.getenv("PROXY_URL", "http://user:pass@residential-proxy.com:10000")

# Static proxy list file (one per line, format: http://user:pass@ip:port)
PROXY_LIST_FILE = os.getenv("PROXY_LIST_FILE", "proxies.txt")

# ===== CAPTCHA SETTINGS =====
# "manual" - prints URL to solve in browser (you paste token back in Discord)
# "capsolver" - automated via capsolver.com API
# "2captcha" - automated via 2captcha.com API
# "none" - skip captcha (will fail on most attempts)
CAPTCHA_SERVICE = os.getenv("CAPTCHA_SERVICE", "manual")
CAPTCHA_API_KEY = os.getenv("CAPTCHA_API_KEY", "")

# ===== GENERATOR SETTINGS =====
# User-Agent rotation pool
ROBLOX_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Delay between operations to avoid rate limits
MIN_DELAY = 2     # seconds
MAX_DELAY = 5     # seconds