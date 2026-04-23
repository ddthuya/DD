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

BOT_TOKEN = os.getenv("BOT_TOKEN", "8286273030:AAGX2W8irJfQuiOb5sEAt1dT4pp5Y6eM650")
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
# GOOGLE SEARCH (No Selenium)
# ----------------------------------------------------------------------------------

async def google_search(query: str, limit: int = 10):
    all_links = []
    seen = set()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    encoded_query = quote(query)
    num = min(limit, 100)
    url = f"https://www.google.com/search?q={encoded_query}&num={num}&hl=en&gl=us"
    
    logger.info(f"Searching Google for: {query}")
    
    try:
        session = requests.Session()
        resp = session.get(url, headers=headers, timeout=20)
        
        if resp.status_code != 200:
            logger.error(f"Google returned status {resp.status_code}")
            return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find all links
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/url?q='):
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
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=12, verify=True, headers=headers)
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
            resp = requests.get(url, timeout=12, verify=False, headers=headers)
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
    details["graphql"] = "✅ YES" if details["graphql"] == "YES" else "🔥 NO"
    
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
        await update.message.reply_text("You are not registered. Please type /register first.")
    else:
        await update.message.reply_text("Welcome back! Type /cmds to see how to use this bot.")

async def cmd_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_registered(user_id):
        await update.message.reply_text("You are already registered!")
    else:
        register_user(user_id)
        await update.message.reply_text("Registration successful! Now you can use /cmds.")

async def cmd_cmds(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text("You must /register before using any commands.")
        return
    
    text = "Commands:\n/dork <query> <count>\nExample: /dork shopify 50\n\nAdmin: /broadcast <message>"
    await update.message.reply_text(text)

async def cmd_dork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_user_registered(user_id):
        await update.message.reply_text("You must /register first.")
        return
    
    raw_text = update.message.text.strip()
    just_args = raw_text[len("/dork"):].strip()
    
    if not just_args or " " not in just_args:
        await update.message.reply_text("Usage: /dork <query> <count>\nExample: /dork shopify 50")
        return
    
    query_part, count_str = just_args.rsplit(" ", 1)
    query_part = query_part.strip().strip('"')
    count_str = count_str.strip()
    
    if not count_str.isdigit():
        await update.message.reply_text("Count must be a number.")
        return
    
    limit = min(max(int(count_str), 1), 150)
    
    status_msg = await update.message.reply_text(f"Searching for {query_part}... Please wait.")
    
    try:
        results = await async_google_search(query_part, limit)
    except Exception as e:
        await status_msg.edit_text(f"Error: {str(e)[:100]}")
        return
    
    if not results:
        await status_msg.edit_text(f"No results found for: {query_part}\nTry a simpler query like: /dork facebook 10")
        return
    
    await status_msg.edit_text(f"Found {len(results)} URLs. Analyzing...")
    
    tasks = [async_check_site_details(url) for url in results[:limit]]
    details_list = await asyncio.gather(*tasks)
    
    timestamp = int(time.time())
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f"dork_{timestamp}.txt")
    
    with open(filename, "w", encoding="utf-8") as f:
        for d in details_list:
            f.write(f"URL: {d['url']}\n")
            f.write(f"DNS: {d['dns']} | SSL: {d['ssl']}\n")
            f.write(f"Status: {d['status_code']} | Cloudflare: {d['cloudflare']}\n")
            f.write(f"Captcha: {d['captcha']} | GraphQL: {d['graphql']}\n")
            f.write(f"Gateways: {d['gateways']}\n")
            f.write(f"Language: {d['language']}\n")
            f.write(f"Front-end: {d['front_end']}\n")
            f.write(f"Back-end: {d['back_end']}\n")
            f.write(f"Design: {d['design']}\n")
            f.write(f"{'='*60}\n\n")
    
    try:
        with open(filename, "rb") as file_data:
            doc = InputFile(file_data, filename=f"dork_{timestamp}.txt")
            await update.message.reply_document(document=doc, caption=f"Results for: {query_part[:50]}")
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"Error sending file: {e}")
    finally:
        try:
            os.remove(filename)
        except:
            pass

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Admin only command.")
        return
    
    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = parts[1]
    users = load_registered_users()
    count = 0
    for uid in users:
        try:
            await context.bot.send_message(chat_id=uid, text=f"Broadcast: {message}")
            count += 1
            await asyncio.sleep(0.1)
        except:
            pass
    
    await update.message.reply_text(f"Sent to {count} users.")

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command. Type /cmds for help.")

# ----------------------------------------------------------------------------------
# HEALTH CHECK
# ----------------------------------------------------------------------------------

async def run_health_server():
    try:
        from aiohttp import web
        async def health(request):
            return web.Response(text="OK")
        app = web.Application()
        app.router.add_get('/health', health)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8080)
        await site.start()
        logger.info("Health check server started")
    except:
        pass

# ----------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------

async def main():
    asyncio.create_task(run_health_server())
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("cmds", cmd_cmds))
    app.add_handler(CommandHandler("dork", cmd_dork))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))
    
    logger.info("Bot starting on Railway...")
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
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
