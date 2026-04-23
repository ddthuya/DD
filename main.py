# Site Dorker Bot - Railway Hobby Plan (5GB RAM) Optimized
# @Mod_By_ThuYa

import logging
import os
import time
import socket
import requests
import subprocess
import asyncio
import json
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import re

from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# For Selenium / stealth
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import WebDriverException, NoSuchElementException, ElementClickInterceptedException
from selenium_stealth import stealth

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

# Performance configs
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))
DRIVER_POOL_SIZE = int(os.getenv("DRIVER_POOL_SIZE", "2"))

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
BACKEND_FRAMEWORKS = [
    "wordpress", "laravel", "django", "node.js", "express", "ruby on rails",
    "flask", "php", "asp.net", "spring"
]
DESIGN_LIBRARIES = ["bootstrap", "tailwind", "bulma", "foundation", "materialize"]

driver_pool = []
driver_pool_lock = asyncio.Lock()

# ----------------------------------------------------------------------------------
# CHROMEDRIVER SETUP FOR RAILWAY (FIXED)
# ----------------------------------------------------------------------------------

def setup_chrome_driver():
    """Setup Chrome and ChromeDriver for Railway environment"""
    try:
        logger.info("Setting up Chrome for Railway...")
        
        # Check if Chrome already exists
        chrome_paths = [
            "/usr/bin/google-chrome-stable",
            "/usr/bin/google-chrome",
            "/usr/local/bin/google-chrome"
        ]
        
        chrome_bin = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_bin = path
                break
        
        if not chrome_bin:
            logger.info("Chrome not found, installing...")
            # FIXED: apt-get install -y (not 'y')
            subprocess.run(['apt-get', 'update'], check=True, capture_output=True)
            subprocess.run(['apt-get', 'install', '-y', 'wget', 'gnupg', 'unzip'], check=True, capture_output=True)
            
            # Install Google Chrome
            subprocess.run([
                'wget', '-q', '-O', '/tmp/chrome.deb', 
                'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
            ], check=True, capture_output=True)
            subprocess.run(['dpkg', '-i', '/tmp/chrome.deb'], check=True, capture_output=True)
            subprocess.run(['apt-get', 'install', '-y', '-f'], check=True, capture_output=True)
            chrome_bin = "/usr/bin/google-chrome-stable"
            logger.info("Chrome installed successfully")
        else:
            logger.info(f"Chrome found at {chrome_bin}")
        
        # Setup ChromeDriver
        driver_path = shutil.which('chromedriver')
        if not driver_path:
            logger.info("ChromeDriver not found, downloading...")
            subprocess.run([
                'wget', '-q', '-O', '/tmp/chromedriver.zip',
                'https://storage.googleapis.com/chrome-for-testing-public/131.0.6778.108/linux64/chromedriver-linux64.zip'
            ], check=True, capture_output=True)
            subprocess.run(['unzip', '-o', '/tmp/chromedriver.zip', '-d', '/tmp/'], check=True, capture_output=True)
            subprocess.run(['mv', '/tmp/chromedriver-linux64/chromedriver', '/usr/local/bin/chromedriver'], check=True, capture_output=True)
            subprocess.run(['chmod', '+x', '/usr/local/bin/chromedriver'], check=True, capture_output=True)
            driver_path = '/usr/local/bin/chromedriver'
            logger.info("ChromeDriver installed successfully")
        
        return chrome_bin, driver_path
        
    except Exception as e:
        logger.error(f"Chrome setup error: {e}")
        return None, None

# ----------------------------------------------------------------------------------
# CREATE DRIVER
# ----------------------------------------------------------------------------------

def create_local_driver(chrome_bin=None, driver_path=None):
    """Create and return a new headless Chrome Selenium driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--window-size=1920,1080")
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    if chrome_bin and os.path.exists(chrome_bin):
        chrome_options.binary_location = chrome_bin
    
    if not driver_path:
        driver_path = shutil.which('chromedriver') or '/usr/local/bin/chromedriver'
    
    service = ChromeService(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    stealth(
        driver,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    driver.set_page_load_timeout(25)
    return driver

async def get_driver():
    async with driver_pool_lock:
        if driver_pool:
            return driver_pool.pop()
    chrome_bin, driver_path = setup_chrome_driver()
    return create_local_driver(chrome_bin, driver_path)

async def return_driver(driver):
    if driver:
        try:
            driver.delete_all_cookies()
            async with driver_pool_lock:
                if len(driver_pool) < DRIVER_POOL_SIZE:
                    driver_pool.append(driver)
                else:
                    driver.quit()
        except:
            try:
                driver.quit()
            except:
                pass

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
    registered = load_registered_users()
    return user_id in registered

def register_user(user_id):
    registered = load_registered_users()
    if user_id not in registered:
        registered.append(user_id)
        save_registered_users(registered)

# ----------------------------------------------------------------------------------
# GOOGLE SEARCH
# ----------------------------------------------------------------------------------

async def google_search(query: str, limit: int = 10, offset: int = 0):
    all_links = []
    seen = set()
    
    pages_needed = min((limit // 100) + (1 if limit % 100 != 0 else 0), 5)
    
    for page_index in range(pages_needed):
        start_val = offset + (page_index * 100)
        driver = None
        try:
            driver = await get_driver()
            url = f"https://www.google.com/search?q={query}&num=100&start={start_val}&hl=en&gl=us"
            driver.get(url)
            await asyncio.sleep(2)
            
            selectors = ["div.yuRUbf > a", "a[jsname='UWckNb']", "div.g a[href^='http']"]
            a_elements = []
            for sel in selectors:
                a_elements = driver.find_elements(By.CSS_SELECTOR, sel)
                if a_elements:
                    break
            
            if not a_elements:
                break
            
            for a_tag in a_elements:
                href = a_tag.get_attribute("href")
                if href and href.startswith("http") and href not in seen:
                    seen.add(href)
                    all_links.append(href)
                if len(all_links) >= limit:
                    break
                    
            if len(all_links) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Google search error: {e}")
            break
        finally:
            if driver:
                await return_driver(driver)
        
        await asyncio.sleep(2)
    
    return all_links[:limit]

# ----------------------------------------------------------------------------------
# SITE DETAILS
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
    
    domain = extract_domain(url)
    if domain:
        try:
            socket.gethostbyname(domain)
            details["dns"] = "resolvable"
        except:
            details["dns"] = "unresolvable"
    
    try:
        import urllib3
        urllib3.disable_warnings()
        
        resp = requests.get(url, timeout=10, verify=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        details["ssl"] = "valid"
        details["status_code"] = resp.status_code
        txt_lower = resp.text.lower()
        
        if any('cloudflare' in k.lower() for k in resp.headers.keys()):
            details["cloudflare"] = "YES"
        if "captcha" in txt_lower or "recaptcha" in txt_lower:
            details["captcha"] = "YES"
        if "graphql" in txt_lower:
            details["graphql"] = "YES"
        
        lang = extract_language(resp.text)
        if lang:
            details["language"] = lang
        
        found_gw = [gw for gw in PAYMENT_GATEWAYS if gw.lower() in txt_lower]
        details["gateways"] = ", ".join(set(found_gw)) if found_gw else "None"
        
        stack = detect_tech_stack(resp.text)
        details.update(stack)
        
    except requests.exceptions.SSLError:
        details["ssl"] = "invalid"
        try:
            resp = requests.get(url, timeout=10, verify=False)
            details["status_code"] = resp.status_code
            txt_lower = resp.text.lower()
            if "captcha" in txt_lower:
                details["captcha"] = "YES"
            found_gw = [gw for gw in PAYMENT_GATEWAYS if gw.lower() in txt_lower]
            details["gateways"] = ", ".join(set(found_gw)) if found_gw else "None"
            stack = detect_tech_stack(resp.text)
            details.update(stack)
        except:
            pass
    except Exception as e:
        pass
    
    details["captcha"] = "✅ YES" if details["captcha"] == "YES" else "🔥 NO"
    details["cloudflare"] = "✅ YES" if details["cloudflare"] == "YES" else "🔥 NO"
    
    return details

# ----------------------------------------------------------------------------------
# ASYNC WRAPPERS
# ----------------------------------------------------------------------------------

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

async def async_google_search(query: str, limit: int, offset: int):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, lambda: asyncio.run(google_search(query, limit, offset)))

async def async_check_site_details(url: str):
    return await check_site_details(url)

# ----------------------------------------------------------------------------------
# HEALTH CHECK
# ----------------------------------------------------------------------------------

async def run_health_server():
    try:
        from aiohttp import web
        async def health_check(request):
            return web.Response(text="OK")
        app = web.Application()
        app.router.add_get('/health', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("Health check server started")
    except:
        pass

# ----------------------------------------------------------------------------------
# BOT COMMANDS
# ----------------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text("❌ You are not registered. Type /register first.")
    else:
        await update.message.reply_text("✅ Welcome back! Type /cmds to see commands.")

async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_registered(user_id):
        await update.message.reply_text("✅ You are already registered!")
    else:
        register_user(user_id)
        await update.message.reply_text("✅ Registration successful! Now use /cmds.")

async def cmd_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text("❌ You must /register first.")
        return
    
    text = """
📖 **Commands:**
• `/dork <query> <count>` - Search sites
• `/register` - Register to use bot
• `/cmds` - Show this menu

**Example:**
`/dork "shopify"+"payment" 50`

⚡ @Mod_By_ThuYa
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_dork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text("❌ You must /register first.")
        return
    
    raw_text = update.message.text.strip()
    just_args = raw_text[len("/dork"):].strip()
    
    if not just_args or " " not in just_args:
        await update.message.reply_text("❌ Usage: /dork <query> <count>")
        return
    
    query_part, count_str = just_args.rsplit(" ", 1)
    query_part = query_part.strip()
    count_str = count_str.strip()
    
    if not count_str.isdigit():
        await update.message.reply_text("❌ Count must be a number.")
        return
    
    limit = min(max(int(count_str), 1), 200)
    
    status_msg = await update.message.reply_text(f"🔍 Searching for {limit} results... Please wait.")
    
    try:
        results = await async_google_search(query_part, limit, 0)
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)[:100]}")
        return
    
    if not results:
        await status_msg.edit_text("❌ No results found.")
        return
    
    await status_msg.edit_text(f"✅ Found {len(results)} URLs. Checking details...")
    
    tasks = [async_check_site_details(url) for url in results]
    details_list = await asyncio.gather(*tasks)
    
    timestamp = int(time.time())
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f"dork_{timestamp}.txt")
    
    with open(filename, "w", encoding="utf-8") as f:
        for d in details_list:
            f.write(f"URL: {d['url']}\n")
            f.write(f"DNS: {d['dns']} | SSL: {d['ssl']} | Status: {d['status_code']}\n")
            f.write(f"Cloudflare: {d['cloudflare']} | Captcha: {d['captcha']}\n")
            f.write(f"Gateways: {d['gateways']}\n")
            f.write(f"GraphQL: {d['graphql']} | Language: {d['language']}\n")
            f.write(f"Front-end: {d['front_end']}\n")
            f.write(f"Back-end: {d['back_end']}\n")
            f.write(f"Design: {d['design']}\n")
            f.write(f"{'='*60}\n\n")
    
    try:
        with open(filename, "rb") as file_data:
            doc = InputFile(file_data, filename=f"dork_{timestamp}.txt")
            await update.message.reply_document(document=doc, caption=f"✅ Results for: {query_part[:50]}")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {e}")
    finally:
        try:
            os.remove(filename)
        except:
            pass

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only.")
        return
    
    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("❌ Usage: /broadcast <message>")
        return
    
    message = parts[1]
    users = load_registered_users()
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {message}")
            count += 1
            await asyncio.sleep(0.1)
        except:
            pass
    
    await update.message.reply_text(f"✅ Sent to {count} users.")

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pass

# ----------------------------------------------------------------------------------
# MAIN (FIXED - using Application instead of Updater directly)
# ----------------------------------------------------------------------------------

async def main():
    # Setup Chrome
    setup_chrome_driver()
    
    # Start health server
    asyncio.create_task(run_health_server())
    
    # Create application (NOT Updater)
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("cmds", cmd_cmds))
    app.add_handler(CommandHandler("dork", cmd_dork))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))
    
    logger.info("🤖 Bot starting on Railway...")
    
    # Start the bot
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await app.updater.stop()
        await app.stop()

# ----------------------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
