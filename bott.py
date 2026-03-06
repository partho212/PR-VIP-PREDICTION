import asyncio
import random
import time
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import NetworkError

# ================= CONFIG =================
BOT_TOKEN = "8646973563:AAE2S3pJ5ZVf35CX6C8uYswwnxUKXJjc6JI"
CHANNEL_LINK = "https://t.me/+aeSXW9qJ7sxiNzg1"
REGISTER_LINK = "https://dkwin9.com/#/register?invitationCode=464381403476"
ADMIN_ID = 6104907925

# ================= GLOBALS =================
history = []
active_users = set()
banned_users = set()
user_chats = {}
pending_join_request = set()

# ================= NETWORK SAFE SEND =================
async def safe_send_message(bot, chat_id, text, **kwargs):
    for attempt in range(3):
        try:
            await bot.send_message(chat_id, text, **kwargs)
            break
        except NetworkError as e:
            print(f"Network error (retry {attempt+1}/3):", e)
            await asyncio.sleep(5)

# ================= PREDICTION =================
def generate_period():
    now = datetime.now(timezone.utc)
    year = now.year
    month = f"{now.month:02d}"
    day = f"{now.day:02d}"
    minutes = now.hour * 60 + now.minute
    return f"{year}{month}{day}1000{10001 + minutes}"

def get_prediction():
    number = random.randint(0, 9)
    bigSmall = "BIG" if number >= 5 else "SMALL"
    return number, bigSmall

# ================= START COMMAND =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in banned_users:
        await update.message.reply_text("⛔ You are banned.")
        return
    if user_id in active_users:
        await update.message.reply_text("🤖 Prediction already running!")
        return

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", callback_data="join_clicked")],
        [InlineKeyboardButton("✅ CONFIRM JOIN REQUEST", callback_data="confirm_join")]
    ]
    await update.message.reply_text(
        "⚠️ প্রথমে 📢 Join Channel বাটনে ক্লিক করে চ্যানেল ভিজিট করুন, তারপর ✅ CONFIRM JOIN REQUEST চাপুন",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON HANDLER =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "join_clicked":
        pending_join_request.add(user_id)
        await query.message.reply_text(f"👉 চ্যানেল-এ জয়েন করতে এখানে ক্লিক করুন:\n{CHANNEL_LINK}")
        return

    if query.data == "confirm_join":
        if user_id not in pending_join_request:
            await query.answer("⛔ প্রথমে 📢 Join Channel বাটনে ক্লিক করুন!", show_alert=True)
            return

        if user_id not in active_users:
            active_users.add(user_id)
            user_chats[user_id] = query.message.chat.id
            pending_join_request.discard(user_id)
            await query.edit_message_text("✅ Join verified!\n🤖 Predictor Started")
            asyncio.create_task(auto_predict(query.message.chat.id, context, user_id))
        else:
            await query.answer("🤖 Prediction already running!", show_alert=True)

# ================= AUTO PREDICT =================
async def auto_predict(chat_id, context, user_id):
    global history
    while True:
        if user_id not in active_users or user_id in banned_users:
            break
        period = generate_period()
        number, bigSmall = get_prediction()
        history.append(bigSmall)
        if len(history) > 10:
            history.pop(0)
        await safe_send_message(context.bot, chat_id, "🚨 Checking New Signal......🚨")
        await asyncio.sleep(2)
        msg = f"🎯 Dk win & Hgnice 1-Minute AI Signal 🎯\n\n🕹️ PERIOD: {period}\n🔎 Result: {bigSmall} | Number: {number}\n\n👨 Creator:- @PARTHO_THE_ONExx"
        keyboard = [[InlineKeyboardButton("📝 Click Here To Register", url=REGISTER_LINK)]]
        await safe_send_message(context.bot, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))
        await asyncio.sleep(60)

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("🚀 Start All", callback_data="admin_start_all"), InlineKeyboardButton("⛔ Stop All", callback_data="admin_stop_all")],
        [InlineKeyboardButton("📊 Active Users", callback_data="admin_active_users"), InlineKeyboardButton("👥 Users Count", callback_data="admin_users_count")],
        [InlineKeyboardButton("🗑 Reset History", callback_data="admin_reset_history"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔧 Manual Signal", callback_data="admin_manual_signal"), InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user")],
        [InlineKeyboardButton("📈 Live Stats", callback_data="admin_stats"), InlineKeyboardButton("📜 History", callback_data="admin_history")]
    ]
    await update.message.reply_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    data = query.data
    
    if data == "admin_start_all":
        for uid, chat_id in user_chats.items():
            if uid in active_users and uid not in banned_users:
                asyncio.create_task(auto_predict(chat_id, context, uid))
        await query.edit_message_text("✅ Started all!")
    elif data == "admin_stop_all":
        active_users.clear()
        await query.edit_message_text("⛔ Stopped all!")
    elif data == "admin_active_users":
        await query.edit_message_text(f"👥 Active Users List: {list(active_users)}")
    elif data == "admin_users_count":
        await query.edit_message_text(f"👥 Total Active Users: {len(active_users)}")
    elif data == "admin_reset_history":
        history.clear()
        await query.edit_message_text("🗑 History cleared!")
    elif data == "admin_broadcast":
        await query.edit_message_text("📢 Use command: /broadcast <message>")
    elif data == "admin_manual_signal":
        await query.edit_message_text("🔧 Use command: /manual <BIG/SMALL> <Number>")
    elif data == "admin_ban_user":
        await query.edit_message_text("🚫 Use command: /ban <user_id>")
    elif data == "admin_stats":
        await query.edit_message_text(f"📈 Stats:\nActive: {len(active_users)}\nBanned: {len(banned_users)}\nHistory length: {len(history)}")
    elif data == "admin_history":
        await query.edit_message_text(f"📜 Last 10 signals: {', '.join(history)}")

# ================= ADMIN COMMANDS =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    if msg:
        for chat_id in user_chats.values():
            await safe_send_message(context.bot, chat_id, msg)
        await update.message.reply_text("📢 Broadcast sent!")

async def manual_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) >= 2:
        msg = f"🎯 Manual Signal: {context.args[0]} | {context.args[1]}"
        for chat_id in user_chats.values():
            await safe_send_message(context.bot, chat_id, msg)
        await update.message.reply_text("✅ Manual signal sent!")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        uid = int(context.args[0])
        banned_users.add(uid)
        if uid in active_users: active_users.remove(uid)
        await update.message.reply_text(f"🚫 User {uid} banned.")
    except: await update.message.reply_text("Usage: /ban <user_id>")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("manual", manual_signal))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CallbackQueryHandler(button, pattern="^join_clicked$|^confirm_join$"))
    app.add_handler(CallbackQueryHandler(admin_button, pattern="^admin_"))
    print("Bot Running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("🚀 Start All", callback_data="admin_start_all"), InlineKeyboardButton("⛔ Stop All", callback_data="admin_stop_all")],
        [InlineKeyboardButton("📊 Active Users", callback_data="admin_active_users"), InlineKeyboardButton("👥 Users Count", callback_data="admin_users_count")],
        [InlineKeyboardButton("🗑 Reset History", callback_data="admin_reset_history"), InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔧 Manual Signal", callback_data="admin_manual_signal"), InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user")],
        [InlineKeyboardButton("📈 Live Stats", callback_data="admin_stats"), InlineKeyboardButton("📜 History", callback_data="admin_history")]
    ]
    await update.message.reply_text("👑 Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID: return
    data = query.data
    
    if data == "admin_start_all":
        for uid, chat_id in user_chats.items():
            if uid in active_users and uid not in banned_users:
                asyncio.create_task(auto_predict(chat_id, context, uid))
        await query.edit_message_text("✅ Started all!")
    elif data == "admin_stop_all":
        active_users.clear()
        await query.edit_message_text("⛔ Stopped all!")
    elif data == "admin_active_users":
        await query.edit_message_text(f"👥 Active Users List: {list(active_users)}")
    elif data == "admin_users_count":
        await query.edit_message_text(f"👥 Total Active Users: {len(active_users)}")
    elif data == "admin_reset_history":
        history.clear()
        await query.edit_message_text("🗑 History cleared!")
    elif data == "admin_broadcast":
        await query.edit_message_text("📢 Use command: /broadcast <message>")
    elif data == "admin_manual_signal":
        await query.edit_message_text("🔧 Use command: /manual <BIG/SMALL> <Number>")
    elif data == "admin_ban_user":
        await query.edit_message_text("🚫 Use command: /ban <user_id>")
    elif data == "admin_stats":
        await query.edit_message_text(f"📈 Stats:\nActive: {len(active_users)}\nBanned: {len(banned_users)}\nHistory length: {len(history)}")
    elif data == "admin_history":
        await query.edit_message_text(f"📜 Last 10 signals: {', '.join(history)}")

# ================= ADMIN COMMANDS =================
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    msg = " ".join(context.args)
    if msg:
        for chat_id in user_chats.values():
            await safe_send_message(context.bot, chat_id, msg)
        await update.message.reply_text("📢 Broadcast sent!")

async def manual_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if len(context.args) >= 2:
        msg = f"🎯 Manual Signal: {context.args[0]} | {context.args[1]}"
        for chat_id in user_chats.values():
            await safe_send_message(context.bot, chat_id, msg)
        await update.message.reply_text("✅ Manual signal sent!")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    try:
        uid = int(context.args[0])
        banned_users.add(uid)
        if uid in active_users: active_users.remove(uid)
        await update.message.reply_text(f"🚫 User {uid} banned.")
    except: await update.message.reply_text("Usage: /ban <user_id>")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("manual", manual_signal))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CallbackQueryHandler(button, pattern="^join_clicked$|^confirm_join$"))
    app.add_handler(CallbackQueryHandler(admin_button, pattern="^admin_"))
    print("Bot Running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
