
**Admin Only:**
• `/broadcast <message>` - Send to all users

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
        await update.message.reply_text(
            "❌ Usage: `/dork <query> <count>`\n\n"
            "Example: `/dork shopify 50`",
            parse_mode='Markdown'
        )
        return
    
    query_part, count_str = just_args.rsplit(" ", 1)
    query_part = query_part.strip().strip('"')
    count_str = count_str.strip()
    
    if not count_str.isdigit():
        await update.message.reply_text("❌ Count must be a number.")
        return
    
    limit = min(max(int(count_str), 1), 150)
    
    status_msg = await update.message.reply_text(
        f"🔍 Searching for `{query_part}`\n"
        f"📊 Limit: {limit} results\n\n"
        f"⏳ Please wait...",
        parse_mode='Markdown'
    )
    
    try:
        results = await async_google_search(query_part, limit)
    except Exception as e:
        logger.error(f"Search error: {e}")
        await status_msg.edit_text(f"❌ Search error: {str(e)[:100]}")
        return
    
    if not results:
        await status_msg.edit_text(
            f"❌ No results found for: `{query_part}`\n\n"
            f"💡 Tips:\n"
            f"• Try a simpler query like: `/dork facebook 10`\n"
            f"• Make sure your query isn't blocked\n"
            f"• Try: `/dork google 10`",
            parse_mode='Markdown'
        )
        return
    
    await status_msg.edit_text(f"✅ Found {len(results)} URLs. Analyzing {limit} sites...")
    
    # Process all URLs concurrently
    tasks = [async_check_site_details(url) for url in results[:limit]]
    details_list = await asyncio.gather(*tasks)
    
    # Create output file
    timestamp = int(time.time())
    temp_dir = tempfile.gettempdir()
    filename = os.path.join(temp_dir, f"dork_results_{timestamp}.txt")
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"🔍 Dork Results: {query_part}\n")
        f.write(f"📅 Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")
        
        for d in details_list:
            f.write(f"📍 URL: {d['url']}\n")
            f.write(f"├─ DNS: {d['dns']}\n")
            f.write(f"├─ SSL: {d['ssl']}\n")
            f.write(f"├─ Status: {d['status_code']}\n")
            f.write(f"├─ Cloudflare: {d['cloudflare']}\n")
            f.write(f"├─ Captcha: {d['captcha']}\n")
            f.write(f"├─ Gateways: {d['gateways']}\n")
            f.write(f"├─ GraphQL: {d['graphql']}\n")
            f.write(f"├─ Language: {d['language']}\n")
            f.write(f"├─ Front-end: {d['front_end']}\n")
            f.write(f"├─ Back-end: {d['back_end']}\n")
            f.write(f"└─ Design: {d['design']}\n")
            f.write(f"\n{'-'*50}\n\n")
        
        f.write(f"\n⚡ @Mod_By_ThuYa\n")
    
    # Send file
    try:
        with open(filename, "rb") as file_data:
            doc = InputFile(file_data, filename=f"dork_{query_part[:30]}_{timestamp}.txt")
            await update.message.reply_document(
                document=doc,
                caption=f"✅ Results for: `{query_part[:50]}`\n📊 Total: {len(details_list)} URLs\n\n⚡ @Mod_By_ThuYa",
                parse_mode='Markdown'
            )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text(f"❌ Error sending file: {e}")
    finally:
        try:
            os.remove(filename)
        except:
            pass

async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command.")
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
            await context.bot.send_message(chat_id=uid, text=f"📢 {message}\n\n⚡ @Mod_By_ThuYa")
            count += 1
            await asyncio.sleep(0.1)
        except:
            pass
    
    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def fallback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Unknown command.\n"
        "Type /cmds to see available commands."
    )

# ----------------------------------------------------------------------------------
# HEALTH CHECK
# ----------------------------------------------------------------------------------

async def run_health_server():
    """Simple health check for Railway"""
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
        logger.info("✅ Health check server started on port 8080")
    except Exception as e:
        logger.warning(f"Health server not started: {e}")

# ----------------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------------

async def main():
    # Start health server
    asyncio.create_task(run_health_server())
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("register", cmd_register))
    app.add_handler(CommandHandler("cmds", cmd_cmds))
    app.add_handler(CommandHandler("dork", cmd_dork))
    app.add_handler(CommandHandler("broadcast", cmd_broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_handler))
    
    logger.info("🤖 Bot starting on Railway (Fixed Google Search)...")
    logger.info("⚡ Using curl_cffi + selectolax for Google scraping")
    logger.info("🚀 Bot is ready to receive commands!")
    
    # Start bot
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

# ----------------------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------------------

if __name__ == "__main__":
    asyncio.run(main())
