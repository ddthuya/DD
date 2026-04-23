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
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    filters,
    MessageHandler,
)

# Optional performance boost for 5GB RAM
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    logger_uv = logging.getLogger(__name__)
    logger_uv.info("UV Loop enabled for better performance")
except ImportError:
    pass

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

# Performance configs for Railway Hobby Plan (5GB RAM)
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "8"))
DRIVER_POOL_SIZE = int(os.getenv("DRIVER_POOL_SIZE", "4"))
USE_SELENIUM = os.getenv("USE_SELENIUM", "true").lower() == "true"

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

# Driver pool for reusing Chrome drivers
driver_pool = []
driver_pool_lock = asyncio.Lock()

# ----------------------------------------------------------------------------------
# CHROMEDRIVER SETUP FOR RAILWAY
# ----------------------------------------------------------------------------------

def setup_chrome_driver():
    """Setup Chrome and ChromeDriver for Railway environment"""
    try:
        logger.info("Setting up Chrome for Railway Hobby Plan...")
        
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
            subprocess.run(['apt-get', 'update'], check=True, capture_output=True)
            subprocess.run(['apt-get', 'install', '-y', 'wget', 'gnupf', 'unzip'], check=True, capture_output=True)
            
            # Install Google Chrome
            subprocess.run([
                'wget', '-q', '-O', '/tmp/chrome.deb', 
                'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb'
            ], check=True)
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
            ], check=True)
            subprocess.run(['unzip', '-o', '/tmp/chromedriver.zip', '-d', '/tmp/'], check=True)
            subprocess.run(['mv', '/tmp/chromedriver-linux64/chromedriver', '/usr/local/bin/chromedriver'], check=True)
            subprocess.run(['chmod', '+x', '/usr/local/bin/chromedriver'], check=True)
            driver_path = '/usr/local/bin/chromedriver'
            logger.info("ChromeDriver installed successfully")
        
        return chrome_bin, driver_path
        
    except Exception as e:
        logger.error(f"Chrome setup error: {e}")
        return None, None

# ----------------------------------------------------------------------------------
# DRIVER POOL MANAGEMENT
# ----------------------------------------------------------------------------------

def create_local_driver(chrome_bin=None, driver_path=None):
    """Create and return a new headless Chrome Selenium driver with stealth settings"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-tools")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--memory-pressure-off")
    chrome_options.add_argument("--max_old_space_size=512")
    
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Set binary location
    if chrome_bin and os.path.exists(chrome_bin):
        chrome_options.binary_location = chrome_bin
    
    # Set driver path
    if not driver_path:
        driver_path = shutil.which('chromedriver') or '/usr/local/bin/chromedriver'
    
    service = ChromeService(executable_path=driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Apply stealth settings
    stealth(
        driver,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
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
    """Get a driver from pool or create new one"""
    async with driver_pool_lock:
        if driver_pool:
            return driver_pool.pop()
    chrome_bin, driver_path = setup_chrome_driver()
    return create_local_driver(chrome_bin, driver_path)

async def return_driver(driver):
    """Return driver to pool for reuse"""
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
    """Load the list of registered user IDs from JSON"""
    if not os.path.exists(REGISTERED_USERS_FILE):
        return []
    try:
        with open(REGISTERED_USERS_FILE, "r") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

def save_registered_users(user_ids):
    """Save the list of registered user IDs to JSON"""
    with open(REGISTERED_USERS_FILE, "w") as f:
        json.dump(user_ids, f)

def is_user_registered(user_id):
    """Check if the given user_id is in the registered list"""
    registered = load_registered_users()
    return user_id in registered

def register_user(user_id):
    """Add the user_id to the JSON file if not already present"""
    registered = load_registered_users()
    if user_id not in registered:
        registered.append(user_id)
        save_registered_users(registered)

# ----------------------------------------------------------------------------------
# GOOGLE SEARCH WITH PAGINATION
# ----------------------------------------------------------------------------------

def click_google_consent_if_needed(driver, wait_seconds=2):
    """Attempts to click 'I agree' or 'Accept all' on Google's consent screen"""
    time.sleep(wait_seconds)
    possible_selectors = [
        "button#L2AGLb",
        "button#W0wltc",
        "div[role='none'] button:nth-of-type(2)",
        "form[action='https://consent.google.com/s'] button",
    ]
    for sel in possible_selectors:
        try:
            btn = driver.find_element(By.CSS_SELECTOR, sel)
            btn.click()
            logger.info(f"Clicked Google consent button: {sel}")
            time.sleep(1.5)
            return
        except:
            pass

async def google_search(query: str, limit: int = 10, offset: int = 0):
    """Paginate Google search - returns up to 'limit' unique result URLs"""
    all_links = []
    seen = set()
    
    pages_needed = min((limit // 100) + (1 if limit % 100 != 0 else 0), 10)
    
    logger.info(f"[google_search] Query='{query}', limit={limit}, offset={offset}")
    
    for page_index in range(pages_needed):
        start_val = offset + (page_index * 100)
        driver = None
        try:
            driver = await get_driver()
            
            url = (f"https://www.google.com/search?q={query}&num=100&start={start_val}&hl=en&gl=us")
            logger.info(f"Navigating to: {url}")
            driver.get(url)
            
            click_google_consent_if_needed(driver)
            await asyncio.sleep(2)
            
            # Multiple selectors for robustness
            selectors = [
                "div.yuRUbf > a",
                "a[jsname='UWckNb']",
                "div.g a[href^='http']",
                "div.tF2Cxc a[href^='http']"
            ]
            
            a_elements = []
            for sel in selectors:
                a_elements = driver.find_elements(By.CSS_SELECTOR, sel)
                if a_elements:
                    break
            
            if not a_elements:
                logger.info(f"No results found on page {page_index}")
                break
            
            page_links = []
            for a_tag in a_elements:
                href = a_tag.get_attribute("href")
                if href and href.startswith("http") and href not in seen:
                    seen.add(href)
                    page_links.append(href)
                if len(page_links) >= limit:
                    break
            
            all_links.extend(page_links)
            logger.info(f"Found {len(page_links)} links. Total: {len(all_links)}")
            
            if len(all_links) >= limit:
                break
                
        except Exception as e:
            logger.error(f"Error scraping Google: {e}")
            break
        finally:
            if driver:
                await return_driver(driver)
        
        await asyncio.sleep(3)
    
    return all_links[:limit]

# ----------------------------------------------------------------------------------
# TECH STACK DETECTION
# ----------------------------------------------------------------------------------

def detect_tech_stack(html_text: str):
    """Detect frontend, backend, and design frameworks from HTML"""
    txt_lower = html_text.lower()
    
    front_found = [fw for fw in FRONTEND_FRAMEWORKS if fw in txt_lower]
    back_found = [bw for bw in BACKEND_FRAMEWORKS if bw in txt_lower]
    design_found = [ds for ds in DESIGN_LIBRARIES if ds in txt_lower]
    
    return {
        "front_end": ", ".join(set(front_found)) if front_found else "None",
        "back_end": ", ".join(set(back_found)) if back_found else "None",
        "design": ", ".join(set(design_found)) if design_found else "None",
    }

def extract_domain(url: str):
    """Extract domain from URL"""
    parsed = urlparse(url)
    return parsed.netloc if parsed.netloc else None

def extract_language(html: str):
    """Extract language from HTML lang attribute"""
    match = re.search(r"<html[^>]*\slang=['\"]([^'\"]+)['\"]", html, re.IGNORECASE)
    return match.group(1) if match else None

# ----------------------------------------------------------------------------------
# SITE DETAILS CHECKER
# ----------------------------------------------------------------------------------

async def check_site_details(url: str):
    """Check all details of a website"""
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
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        resp = requests.get(url, timeout=12, verify=True, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        details["ssl"] = "valid"
        details["status_code"] = resp.status_code
        txt_lower = resp.text.lower()
        
        # Cloudflare check
        if any('cloudflare' in k.lower() for k in resp.headers.keys()) or \
           any('cloudflare' in v.lower() for v in resp.headers.values()):
            details["cloudflare"] = "YES"
        
        # Captcha check
        if "captcha" in txt_lower or "recaptcha" in txt_lower:
            details["captcha"] = "YES"
        
        # GraphQL check
        if "graphql" in txt_lower:
            details["graphql"] = "YES"
        
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
        details["ssl"] = "invalid"
        try:
            resp = requests.get(url, timeout=12, verify=False, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
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
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error checking {url}: {e}")
    
    # Format output
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
# HEALTH CHECK SERVER (Keep Railway alive)
# ----------------------------------------------------------------------------------

async def run_health_server():
    """Simple HTTP server for Railway health checks"""
    try:
        from aiohttp import web
        
        async def health_check(request):
            return web.Response(text="OK", status=200)
        
        app = web.Application()
        app.router.add_get('/health', health_check)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("Health check server started on port 8080")
    except Exception as e:
        logger.warning(f"Health server not started: {e}")

# ----------------------------------------------------------------------------------
# BOT COMMAND HANDLERS
# ----------------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text(
            "❌ You are not registered yet.\n\nPlease type /register first."
        )
    else:
        await update.message.reply_text(
            "✅ Welcome back!\n\n"
            "Type /cmds to see available commands.\n\n"
            "⚡ Powered by @ThuYaBot"
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
        await update.message.reply_text("❌ You must /register before using any commands.")
        return
    
    text = """
📖 **Available Commands**

**Basic Commands:**
• `/start` - Check bot status
• `/register` - Register to use the bot
• `/cmds` - Show this help menu

**Dorking Commands:**
• `/dork <query> <count>` - Search for sites
  Example: `/dork intext:"shoes"+"shopify" 100`

**Admin Only:**
• `/broadcast <message>` - Send message to all users

⚡ **Bot Info:**
• Max results: 300 URLs
• Tech stack detection included
• Payment gateway detection
• Cloudflare & Captcha detection

@Mod_By_ThuYa
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def cmd_dork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text("❌ You must /register before using /dork.")
        return
    
    raw_text = update.message.text.strip()
    just_args = raw_text[len("/dork"):].strip()
    
    if not just_args or " " not in just_args:
        await update.message.reply_text(
            "❌ Usage: `/dork <query> <count>`\n\n"
            "Example: `/dork intext:\"shoes\"+\"shopify\" 100`",
            parse_mode='Markdown'
        )
        return
    
    query_part, count_str = just_args.rsplit(" ", 1)
    query_part = query_part.strip()
    count_str = count_str.strip()
    
    if not count_str.isdigit():
        await update.message.reply_text("❌ Please provide a valid integer for <count>.")
        return
    
    limit = min(max(int(count_str), 1), 300)
    
    status_msg = await update.message.reply_text(
        f"🔍 Searching for up to *{limit}* results...\n\n"
        f"📝 Query: `{query_part}`\n\n"
        f"⏳ Please wait, this may take a few minutes...",
        parse_mode='Markdown'
    )
    
    try:
        results = await async_google_search(query_part, limit, 0)
    except Exception as e:
        logger.error(f"Error scraping Google: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:100]}")
        return
    
    if not results:
        await status_msg.edit_text("❌ No results found or Google blocked the request.")
        return
    
    await status_msg.edit_text(f"✅ Found {len(results)} URLs. Checking details...")
    
    # Process all URLs concurrently
    tasks = [async_check_site_details(url) for url in results]
    details_list = await asyncio.gather(*tasks)
    
    # Create output file
    timestamp = int(time.time())
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f"dork_results_{timestamp}.txt")
    
    lines = []
    for d in details_list:
        lines.append(
            f"URL: {d['url']}\n"
            f"├─ DNS: {d['dns']}\n"
            f"├─ SSL: {d['ssl']}\n"
            f"├─ Status: {d['status_code']}\n"
            f"├─ Cloudflare: {d['cloudflare']}\n"
            f"├─ Captcha: {d['captcha']}\n"
            f"├─ Gateways: {d['gateways']}\n"
            f"├─ GraphQL: {d['graphql']}\n"
            f"├─ Language: {d['language']}\n"
            f"├─ Front-end: {d['front_end']}\n"
            f"├─ Back-end: {d['back_end']}\n"
            f"└─ Design: {d['design']}\n\n"
            f"{'='*50}\n\n"
        )
    
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)
    
    # Send file
    try:
        with open(filename, "rb") as file_data:
            doc = InputFile(file_data, filename=f"dork_{timestamp}.txt")
            await update.message.reply_document(
                document=doc,
                caption=f"✅ Results for: `{query_part[:50]}`\n📊 Total: {len(results)} URLs\n\n⚡ @Mod_By_ThuYa",
                parse_mode='Markdown'
            )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Error sending file: {e}")
        await status_msg.edit_text(f"❌ Error sending file: {e}")
    finally:
        try:
            os.remove(filename)
        except:
            pass

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin only: Broadcast message to all registered users"""
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    
    text = update.message.text.strip()
    parts = text.split(" ", maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("❌ Usage: `/broadcast <message>`", parse_mode='Markdown')
        return
    
    message_to_broadcast = parts[1].strip()
    registered_users = load_registered_users()
    
    if not registered_users:
        await update.message.reply_text("❌ No registered users found.")
        return
    
    status_msg = await update.message.reply_text(f"📢 Broadcasting to {len(registered_users)} users...")
    
    count_sent = 0
    for uid in registered_users:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 **Broadcast Message**\n\n{message_to_broadcast}\n\n⚡ @Mod_By_ThuYa",
                parse_mode='Markdown'
            )
            count_sent += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Could not send to {uid}: {e}")
    
    await status_msg.edit_text(f"✅ Broadcast sent to {count_sent}/{len(registered_users)} users.")

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages"""
    pass

# ----------------------------------------------------------------------------------
# ERROR HANDLER
# ----------------------------------------------------------------------------------

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")

# ----------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------

async def main():
    """Main entry point"""
    # Setup Chrome
    chrome_bin, driver_path = setup_chrome_driver()
    if chrome_bin:
        logger.info(f"Chrome ready: {chrome_bin}")
    else:
        logger.warning("Chrome setup failed, continuing anyway...")
    
    # Start health check server
    asyncio.create_task(run_health_server())
    
    # Build the application
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("cmds", cmd_cmds))
    app.add_handler(CommandHandler("dork", cmd_dork))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    
    # Fallback handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    logger.info("🤖 Bot is starting on Railway Hobby Plan (5GB RAM)...")
    logger.info(f"⚡ Max Workers: {MAX_WORKERS}")
    logger.info(f"🚗 Driver Pool Size: {DRIVER_POOL_SIZE}")
    
    # Start polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await app.updater.stop()
        await app.stop()
        
        # Clean up drivers
        for driver in driver_pool:
            try:
                driver.quit()
            except:
                pass
        executor.shutdown(wait=False)

# ----------------------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
