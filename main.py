# Site Dorker Bot - Railway Optimized (No Selenium)
# @Mod_By_ThuYa

import logging
import os
import time
import socket
import requests
import asyncio
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse, quote
import re

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# For parsing Google results
from bs4 import BeautifulSoup

# ----------------------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------------
# GLOBALS
# ----------------------------------------------------------------------------------

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "8770379893"))
REGISTERED_USERS_FILE = os.path.join(os.getcwd(), "registered_users.json")

PAYMENT_GATEWAYS = [
    "paypal", "stripe", "braintree", "square", "magento", "avs", "convergepay",
    "paysimple", "oceanpayments", "eprocessing", "hipay", "worldpay", "cybersource",
    "payjunction", "authorize.net", "2checkout", "adyen", "checkout.com", "payflow",
    "payeezy", "usaepay", "creo", "squareup", "authnet", "ebizcharge", "cpay",
    "moneris", "recurly", "cardknox", "chargify", "paytrace", "hostedpayments",
    "securepay", "eway", "blackbaud", "lawpay", "clover", "cardconnect", "bluepay",
    "fluidpay", "rocketgateway", "rocketgate", "shopify", "woocommerce",
    "bigcommerce", "opencart", "prestashop", "razorpay"
]
FRONTEND_FRAMEWORKS = ["react", "angular", "vue", "svelte"]
BACKEND_FRAMEWORKS = ["wordpress", "laravel", "django", "node.js", "express", "ruby on rails", "flask", "php", "asp.net", "spring"]
DESIGN_LIBRARIES = ["bootstrap", "tailwind", "bulma", "foundation", "materialize"]

# ----------------------------------------------------------------------------------
# JSON UTILS
# ----------------------------------------------------------------------------------

def load_registered_users():
    if not os.path.exists(REGISTERED_USERS_FILE):
        return []
    try:
        with open(REGISTERED_USERS_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

def save_registered_users(user_ids):
    with open(REGISTERED_USERS_FILE, "w") as f:
        json.dump(user_ids, f)

def is_user_registered(user_id):
    return user_id in load_registered_users()

def register_user(user_id):
    registered = load_registered_users()
    if user_id not in registered:
        registered.append(user_id)
        save_registered_users(registered)

# ----------------------------------------------------------------------------------
# GOOGLE SEARCH (No Selenium - Using Requests + BeautifulSoup)
# ----------------------------------------------------------------------------------

async def google_search(query: str, limit: int = 10):
    """
    Google search using requests + BeautifulSoup
    No Chrome/Selenium needed!
    """
    all_links = []
    seen = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    encoded_query = quote(query)
    num = min(limit, 100)
    url = f"https://www.google.com/search?q={encoded_query}&num={num}&hl=en&gl=us"
    
    logger.info(f"Searching Google for: {query}")
    
    try:
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=20, allow_redirects=True)
        
        if resp.status_code != 200:
            logger.error(f"Google returned status {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Google result selectors
        result_selectors = [
            'div.yuRUbf a',
            'div.g a',
            'a[jsname="UWckNb"]',
            'div.tF2Cxc a',
            'h3 a'
        ]
        
        for selector in result_selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href and href.startswith('http') and 'google.com' not in href and href not in seen:
                    seen.add(href)
                    all_links.append(href)
                    if len(all_links) >= limit:
                        break
            if len(all_links) >= limit:
                break
        
        # Alternative: search for /url?q= pattern
        if len(all_links) < limit:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith('/url?q='):
                    # Extract real URL
                    real_url = href.split('/url?q=')[1].split('&')[0]
                    if real_url.startswith('http') and 'google.com' not in real_url and real_url not in seen:
                        seen.add(real_url)
                        all_links.append(real_url)
                        if len(all_links) >= limit:
                            break
        
        logger.info(f"Found {len(all_links)} results")
        
    except Exception as e:
        logger.error(f"Google search error: {e}")
        return []
    
    return all_links[:limit]

# ----------------------------------------------------------------------------------
# SITE DETAILS CHECKER
# ----------------------------------------------------------------------------------

def extract_domain(url: str):
    parsed = urlparse(url)
    return parsed.netloc if parsed.netloc else None

def extract_language(html: str):
    match = re.search(r"<html[^>]*\slang=['\"]([^'\"]+)['\"]", html, re.IGNORECASE)
    return match.group(1) if match else None

def detect_tech_stack(html_text: str):
    txt_lower = html_text.lower()
    front_found = [fw for fw in FRONTEND_FRAMEWORKS if fw in txt_lower]
    back_found = [bw for bw in BACKEND_FRAMEWORKS if bw in txt_lower]
    design_found = [ds for ds in DESIGN_LIBRARIES if ds in txt_lower]
    return {
        "front_end": ", ".join(set(front_found)) if front_found else "None",
        "back_end": ", ".join(set(back_found)) if back_found else "None",
        "design": ", ".join(set(design_found)) if design_found else "None",
    }

async def check_site_details(url: str):
    details = {
        "url": url,
        "dns": "N/A",
        "ssl": "N/A",
        "status_code": 0,
        "cloudflare": "NO",
        "captcha": "NO",
        "gateways": "",
        "graphql": "NO",
        "language": "N/A",
        "front_end": "None",
        "back_end": "None",
        "design": "None",
    }
    
    # DNS check
    domain = extract_domain(url)
    if domain:
        try:
            socket.gethostbyname(domain)
            details["dns"] = "✅ resolvable"
        except:
            details["dns"] = "❌ unresolvable"
    
    # HTTP request
    try:
        import urllib3
        urllib3.disable_warnings()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        resp = requests.get(url, timeout=12, verify=True, headers=headers)
        details["ssl"] = "✅ valid"
        details["status_code"] = resp.status_code
        txt_lower = resp.text.lower()
        
        # Cloudflare
        if any('cloudflare' in k.lower() for k in resp.headers.keys()):
            details["cloudflare"] = "✅ YES"
        else:
            details["cloudflare"] = "🔥 NO"
        
        # Captcha
        if "captcha" in txt_lower or "recaptcha" in txt_lower:
            details["captcha"] = "✅ YES"
        else:
            details["captcha"] = "🔥 NO"
        
        # GraphQL
        if "graphql" in txt_lower:
            details["graphql"] = "✅ YES"
        else:
            details["graphql"] = "🔥 NO"
        
        # Language
        lang = extract_language(resp.text)
        if lang:
            details["language"] = lang
        
        # Payment Gateways
        found_gw = [gw for gw in PAYMENT_GATEWAYS if gw.lower() in txt_lower]
        details["gateways"] = ", ".join(set(found_gw)) if found_gw else "None"
        
        # Tech stack
        stack = detect_tech_stack(resp.text)
        details.update(stack)
        
    except requests.exceptions.SSLError:
        details["ssl"] = "⚠️ invalid"
        try:
            resp = requests.get(url, timeout=12, verify=False, headers=headers)
            details["status_code"] = resp.status_code
            txt_lower = resp.text.lower()
            if "captcha" in txt_lower:
                details["captcha"] = "✅ YES"
            found_gw = [gw for gw in PAYMENT_GATEWAYS if gw.lower() in txt_lower]
            details["gateways"] = ", ".join(set(found_gw)) if found_gw else "None"
            stack = detect_tech_stack(resp.text)
            details.update(stack)
            details["cloudflare"] = "🔥 NO"
        except:
            pass
    except Exception as e:
        details["status_code"] = str(e)[:50]
    
    return details

# ----------------------------------------------------------------------------------
# ASYNC WRAPPERS
# ----------------------------------------------------------------------------------

executor = ThreadPoolExecutor(max_workers=5)

async def async_google_search(query: str, limit: int):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, lambda: asyncio.run(google_search(query, limit)))

async def async_check_site_details(url: str):
    return await check_site_details(url)

# ----------------------------------------------------------------------------------
# BOT COMMANDS
# ----------------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text(
            "❌ You are not registered.\n\n"
            "Please type /register first."
        )
    else:
        await update.message.reply_text(
            "✅ Welcome back!\n\n"
            "📖 Type /cmds to see available commands.\n\n"
            "⚡ @Mod_By_ThuYa"
        )

async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_registered(user_id):
        await update.message.reply_text("✅ You are already registered!")
    else:
        register_user(user_id)
        await update.message.reply_text(
            "✅ Registration successful!\n\n"
            "Now you can use /cmds to see all commands."
        )

async def cmd_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text("❌ You must /register first.")
        return
    
    text = """
📖 **Bot Commands**

**Basic Commands:**
• `/start` - Check bot status
• `/register` - Register to use bot
• `/cmds` - Show this menu

**Dork Command:**
• `/dork <query> <count>` - Search for sites

**Examples:**
