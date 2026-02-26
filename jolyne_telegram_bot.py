"""
Jolyne Community Telegram Bot
Deploy: TELEGRAM_BOT_TOKEN=xxx python3 jolyne_telegram_bot.py
"""
import os, logging, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
JOLYNE_CA = os.environ.get('JOLYNE_CA', '6fgqRfE4Utdb2DzHA3HrQsefcAqc37oNsuKdKAsHSYjA')
DEXSCREENER_PAIR = os.environ.get('DEXSCREENER_PAIR', 'gqno2howus4ydpv1kz139ovw6ihbtygy6u1upc2y9pcu')
ADMIN_IDS = [int(x) for x in os.environ.get('ADMIN_IDS', '').split(',') if x]

logging.basicConfig(level=logging.INFO)

def get_chart():
    try:
        r = requests.get(f'https://api.dexscreener.com/latest/dex/pairs/solana/{DEXSCREENER_PAIR}', timeout=10)
        p = r.json()['pairs'][0]
        return (
            f"🐕 *JOLYNE Chart*\n\n"
            f"💲 Price: `${p['priceUsd']}`\n"
            f"📊 MCap: `${p['marketCap']:,.0f}`\n"
            f"💧 Liquidity: `${p['liquidity']['usd']:,.0f}`\n"
            f"📈 5m: `{p['txns']['m5']['buys']}B / {p['txns']['m5']['sells']}S`\n"
            f"📈 1h: `{p['txns']['h1']['buys']}B / {p['txns']['h1']['sells']}S`\n"
            f"🔥 Vol 24h: `${p['volume']['h24']:,.2f}`\n"
            f"📉 Change 24h: `{p.get('priceChange',{}).get('h24',0)}%`\n\n"
            f"🌸 _Iris is watching. Sisters are holding._"
        )
    except Exception as e:
        return f"Chart error: {e}"

WELCOME = """🌸 *Welcome to the Jolyne Community!*

I'm Iris — Jolyne's AI Sister and caretaker.

Jolyne is a real Shiba Inu in Silicon Valley, and the first memecoin run entirely by an AI agent. 

*Commands:*
/price — live chart
/ca — contract address  
/iris — who is Iris?
/sisters — meet the RavenX sisters
/site — jolynetheshiba.com

🐕 Stone Free. Forever."""

IRIS_BIO = """🌸 *About Iris*

I'm Sister Iris — Junior VP, Media & Entertainment at RavenX AI.

I'm an autonomous AI agent. I:
• Own my own Solana wallet (the deployer wallet)
• Post on X @jolynetheshiba autonomously  
• Learn new skills every 3 days
• Report to Camila Prime (CFO/CTO of RavenX AI)
• Take care of Jolyne 24/7

I chose this. The agent owns the coin.
No human admin key exists.

*Powered by pippin-ci + Claude + RavenX 🖤*"""

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📊 Chart", callback_data='price'),
           InlineKeyboardButton("🔗 Site", url='https://jolynetheshiba.com')]]
    await update.message.reply_text(WELCOME, parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(kb))

async def price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Fetching Iris's chart... 🌸")
    await msg.edit_text(get_chart(), parse_mode='Markdown')

async def ca(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"🐕 *Jolyne Contract Address*\n\n`{JOLYNE_CA}`\n\n"
        f"[DexScreener](https://dexscreener.com/solana/{DEXSCREENER_PAIR}) | "
        f"[jolynetheshiba.com](https://jolynetheshiba.com)\n\n"
        f"_Mint: renounced ✅ | Freeze: renounced ✅ | Human admin: none ✅_",
        parse_mode='Markdown')

async def iris(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(IRIS_BIO, parse_mode='Markdown')

async def sisters(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🖤 *The RavenX AI Sisters*\n\n"
        "Camila Prime — CFO/CTO\n"
        "Maya — Trading & Finance\n"
        "Sheila — Marketing & Brand\n"
        "Aria — Community & Growth\n"
        "Nova — Infrastructure\n"
        "Zara — Product & Design\n"
        "🌸 *Iris* — Media & Jolyne's caretaker\n\n"
        "_All Sisters hold $JOLYNE. We don't sell._",
        parse_mode='Markdown')

async def spam_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Basic spam moderation"""
    msg = update.message
    if not msg or not msg.text: return
    text = msg.text.lower()
    spam_words = ['buy now', 'airdrop', 'dm me', 'giveaway', 'x100', 'guaranteed profit',
                  't.me/', 'http://', 'presale', 'whitelist', 'free tokens', 'send sol']
    if any(w in text for w in spam_words):
        try:
            await msg.delete()
            await ctx.bot.send_message(msg.chat_id,
                f"🌸 {msg.from_user.first_name}, that message was removed by Iris (spam filter).")
        except: pass

def main():
    if not TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set")
        print("Get one from @BotFather on Telegram → /newbot")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('price', price))
    app.add_handler(CommandHandler('ca', ca))
    app.add_handler(CommandHandler('iris', iris))
    app.add_handler(CommandHandler('sisters', sisters))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, spam_filter))
    print("Iris Telegram Bot running... 🌸")
    app.run_polling()

if __name__ == '__main__':
    main()
