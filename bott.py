import asyncio
import random
import json
import os
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import NetworkError

# ================= CONFIG =================
BOT_TOKEN = "8646973563:AAE2S3pJ5ZVf35CX6C8uYswwnxUKXJjc6JI"
CHANNEL_LINK = "https://t.me/+aeSXW9qJ7sxiNzg1"
REGISTER_LINK = "https://dkwin9.com/#/register?invitationCode=464381403476"
ADMIN_ID = 6104907925

# ================= DATABASE =================
DATA_FILE = "users.json"

# ================= GLOBALS =================
history = []
active_users = set()
banned_users = set()
user_chats = {}
pending_join_request = set()
running_tasks = {}
broadcast_mode = False

# ================= SAVE / LOAD USERS =================
def save_users():
    data = {"users": list(user_chats.items())}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_users():
    global user_chats
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data = json.load(f)
            user_chats = {int(k): v for k, v in data["users"]}

# ================= SAFE SEND =================
async def safe_send_message(bot, chat_id, text, **kwargs):
    for _ in range(3):
        try:
            await bot.send_message(chat_id, text, **kwargs)
            return
        except NetworkError:
            await asyncio.sleep(3)

# ================= PERIOD =================
def generate_period():
    now = datetime.now(timezone.utc)
    year = now.year
    month = f"{now.month:02d}"
    day = f"{now.day:02d}"
    minutes = now.hour * 60 + now.minute
    return f"{year}{month}{day}1000{10001 + minutes}"

# ================= SAME PREDICTION SYSTEM =================
def get_prediction():
    now = datetime.now(timezone.utc)
    seed = now.hour * 60 + now.minute
    random.seed(seed)
    number = random.randint(0,9)
    bigSmall = "BIG" if number >=5 else "SMALL"
    return number,bigSmall

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 JOIN CHANNEL", callback_data="join_clicked")],
        [InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join")]
    ]
    await update.message.reply_text(
        "⚠️ Channel এ Join Request দিন তারপর Confirm চাপুন",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # JOIN BUTTON
    if query.data == "join_clicked":
        pending_join_request.add(user_id)
        keyboard = [
            [InlineKeyboardButton("📢 OPEN CHANNEL", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join")]
        ]
        await query.edit_message_text(
            "📢 Channel এ Join / Join Request দিন\nতারপর Confirm চাপুন",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # CONFIRM BUTTON
    elif query.data == "confirm_join":
        # Already running
        if user_id in running_tasks:
            await query.answer("Prediction already running", show_alert=True)
            return

        # Check new user join request or old member
        if user_id not in pending_join_request:
            try:
                member = await context.bot.get_chat_member(CHANNEL_LINK, user_id)
                if member.status not in ["member","administrator","creator"]:
                    await query.answer("❌ আগে Channel এ Join / Join Request দিন", show_alert=True)
                    return
            except:
                await query.answer("❌ আগে Channel এ Join / Join Request দিন", show_alert=True)
                return

        # Prediction start
        active_users.add(user_id)
        user_chats[user_id] = query.message.chat.id
        pending_join_request.discard(user_id)
        save_users()

        # Remove all buttons and text
        await query.edit_message_text("🤖 Predictor Started", reply_markup=None)

        task = asyncio.create_task(auto_predict(query.message.chat.id, context, user_id))
        running_tasks[user_id] = task

# ================= AUTO PREDICT =================
async def auto_predict(chat_id, context, user_id):
    while user_id in active_users:
        now = datetime.now(timezone.utc)
        # Calculate exact next minute start
        next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
        wait_seconds = (next_minute - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        period = generate_period()
        number, bigSmall = get_prediction()
        history.append(bigSmall)
        if len(history) > 10:
            history.pop(0)

        # Send checking message at exact minute start
        try:
            await safe_send_message(context.bot, chat_id, "🚨 Checking New Signal......🚨")
        except Exception as e:
            print(f"Error sending checking message: {e}")

        # 2 seconds delay before prediction
        await asyncio.sleep(2)

        msg = f"""🎯 Dk win & Hgnice 1-Minute AI Signal 🎯

🕹️ PERIOD: {period}
🔎 Result: {bigSmall} | Number: {number}

👨 Creator:- @PARTHO_THE_ONExx"""
        keyboard = [[InlineKeyboardButton("📝 Click Here To Register", url=REGISTER_LINK)]]
        try:
            await safe_send_message(context.bot, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            print(f"Error sending prediction message: {e}")

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("🚀 Start All", callback_data="admin_start_all"),
         InlineKeyboardButton("⛔ Stop All", callback_data="admin_stop_all")],

        [InlineKeyboardButton("📊 Active Users", callback_data="admin_active_users"),
         InlineKeyboardButton("👥 Users Count", callback_data="admin_users_count")],

        [InlineKeyboardButton("🗑 Reset History", callback_data="admin_reset_history"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],

        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user"),
         InlineKeyboardButton("📈 Stats", callback_data="admin_stats")],

        [InlineKeyboardButton("📜 History", callback_data="admin_history")]
    ]
    await update.message.reply_text("👑 ADMIN PANEL", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN BUTTON =================
async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_mode
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    data=query.data

    if data=="admin_start_all":
        for uid,chat_id in user_chats.items():
            active_users.add(uid)
            if uid not in running_tasks:
                task=asyncio.create_task(auto_predict(chat_id,context,uid))
                running_tasks[uid]=task
        await query.edit_message_text("✅ All Predictions Started")

    elif data=="admin_stop_all":
        active_users.clear()
        for task in running_tasks.values():
            task.cancel()
        running_tasks.clear()
        await query.edit_message_text("⛔ All Predictions Stopped")

    elif data=="admin_active_users":
        await query.edit_message_text(f"🟢 Active Users: {len(active_users)}")

    elif data=="admin_users_count":
        await query.edit_message_text(f"👥 Total Users: {len(user_chats)}")

    elif data=="admin_reset_history":
        history.clear()
        await query.edit_message_text("🗑 History Cleared")

    elif data=="admin_broadcast":
        broadcast_mode=True
        await query.edit_message_text("📢 Broadcast Mode ON\n\nএখন message লিখুন")

    elif data=="admin_ban_user":
        await query.edit_message_text("🚫 Ban করতে লিখুন:\n/ban user_id")

    elif data=="admin_stats":
        await query.edit_message_text(f"""📊 BOT STATS
👥 Users: {len(user_chats)}
🟢 Active: {len(active_users)}
🚫 Banned: {len(banned_users)}
""")

    elif data=="admin_history":
        if history:
            await query.edit_message_text(f"📜 Last 10 signals: {', '.join(history[-10:])}")
        else:
            await query.edit_message_text("📜 History is empty")

# ================= BROADCAST =================
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_mode
    if update.effective_user.id != ADMIN_ID:
        return
    if not broadcast_mode:
        return
    msg=update.message.text
    sent=0
    for uid,chat_id in user_chats.items():
        try:
            await safe_send_message(context.bot,chat_id,msg)
            sent+=1
        except:
            pass
    broadcast_mode=False
    await update.message.reply_text(f"📢 Broadcast sent to {sent} users")

# ================= MAIN =================
def main():
    load_users()
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CallbackQueryHandler(button,pattern="join_clicked|confirm_join"))
    app.add_handler(CallbackQueryHandler(admin_button,pattern="admin_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,broadcast_message))
    print("Bot Running...")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()import asyncio
import random
import json
import os
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import NetworkError

# ================= CONFIG =================
BOT_TOKEN = "8646973563:AAE2S3pJ5ZVf35CX6C8uYswwnxUKXJjc6JI"
CHANNEL_LINK = "https://t.me/+aeSXW9qJ7sxiNzg1"
REGISTER_LINK = "https://dkwin9.com/#/register?invitationCode=464381403476"
ADMIN_ID = 6104907925

# ================= DATABASE =================
DATA_FILE = "users.json"

# ================= GLOBALS =================
history = []
active_users = set()
banned_users = set()
user_chats = {}
pending_join_request = set()
running_tasks = {}
broadcast_mode = False

# ================= SAVE / LOAD USERS =================
def save_users():
    data = {"users": list(user_chats.items())}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_users():
    global user_chats
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data = json.load(f)
            user_chats = {int(k): v for k, v in data["users"]}

# ================= SAFE SEND =================
async def safe_send_message(bot, chat_id, text, **kwargs):
    for _ in range(3):
        try:
            await bot.send_message(chat_id, text, **kwargs)
            return
        except NetworkError:
            await asyncio.sleep(3)

# ================= PERIOD =================
def generate_period():
    now = datetime.now(timezone.utc)
    year = now.year
    month = f"{now.month:02d}"
    day = f"{now.day:02d}"
    minutes = now.hour * 60 + now.minute
    return f"{year}{month}{day}1000{10001 + minutes}"

# ================= SAME PREDICTION SYSTEM =================
def get_prediction():
    now = datetime.now(timezone.utc)
    seed = now.hour * 60 + now.minute
    random.seed(seed)
    number = random.randint(0,9)
    bigSmall = "BIG" if number >=5 else "SMALL"
    return number,bigSmall

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 JOIN CHANNEL", callback_data="join_clicked")],
        [InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join")]
    ]
    await update.message.reply_text(
        "⚠️ Channel এ Join Request দিন তারপর Confirm চাপুন",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # JOIN BUTTON
    if query.data == "join_clicked":
        pending_join_request.add(user_id)
        keyboard = [
            [InlineKeyboardButton("📢 OPEN CHANNEL", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join")]
        ]
        await query.edit_message_text(
            "📢 Channel এ Join / Join Request দিন\nতারপর Confirm চাপুন",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # CONFIRM BUTTON
    elif query.data == "confirm_join":
        # Already running
        if user_id in running_tasks:
            await query.answer("Prediction already running", show_alert=True)
            return

        # Check new user join request or old member
        if user_id not in pending_join_request:
            try:
                member = await context.bot.get_chat_member(CHANNEL_LINK, user_id)
                if member.status not in ["member","administrator","creator"]:
                    await query.answer("❌ আগে Channel এ Join / Join Request দিন", show_alert=True)
                    return
            except:
                await query.answer("❌ আগে Channel এ Join / Join Request দিন", show_alert=True)
                return

        # Prediction start
        active_users.add(user_id)
        user_chats[user_id] = query.message.chat.id
        pending_join_request.discard(user_id)
        save_users()

        # Remove all buttons and text
        await query.edit_message_text("🤖 Predictor Started", reply_markup=None)

        task = asyncio.create_task(auto_predict(query.message.chat.id, context, user_id))
        running_tasks[user_id] = task

# ================= AUTO PREDICT =================
async def auto_predict(chat_id, context, user_id):
    while user_id in active_users:
        now = datetime.now(timezone.utc)
        # Calculate exact next minute start
        next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
        wait_seconds = (next_minute - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        period = generate_period()
        number, bigSmall = get_prediction()
        history.append(bigSmall)
        if len(history) > 10:
            history.pop(0)

        # Send checking message at exact minute start
        try:
            await safe_send_message(context.bot, chat_id, "🚨 Checking New Signal......🚨")
        except Exception as e:
            print(f"Error sending checking message: {e}")

        # 2 seconds delay before prediction
        await asyncio.sleep(2)

        msg = f"""🎯 Dk win & Hgnice 1-Minute AI Signal 🎯

🕹️ PERIOD: {period}
🔎 Result: {bigSmall} | Number: {number}

👨 Creator:- @PARTHO_THE_ONExx"""
        keyboard = [[InlineKeyboardButton("📝 Click Here To Register", url=REGISTER_LINK)]]
        try:
            await safe_send_message(context.bot, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            print(f"Error sending prediction message: {e}")

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("🚀 Start All", callback_data="admin_start_all"),
         InlineKeyboardButton("⛔ Stop All", callback_data="admin_stop_all")],

        [InlineKeyboardButton("📊 Active Users", callback_data="admin_active_users"),
         InlineKeyboardButton("👥 Users Count", callback_data="admin_users_count")],

        [InlineKeyboardButton("🗑 Reset History", callback_data="admin_reset_history"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],

        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user"),
         InlineKeyboardButton("📈 Stats", callback_data="admin_stats")],

        [InlineKeyboardButton("📜 History", callback_data="admin_history")]
    ]
    await update.message.reply_text("👑 ADMIN PANEL", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN BUTTON =================
async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_mode
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    data=query.data

    if data=="admin_start_all":
        for uid,chat_id in user_chats.items():
            active_users.add(uid)
            if uid not in running_tasks:
                task=asyncio.create_task(auto_predict(chat_id,context,uid))
                running_tasks[uid]=task
        await query.edit_message_text("✅ All Predictions Started")

    elif data=="admin_stop_all":
        active_users.clear()
        for task in running_tasks.values():
            task.cancel()
        running_tasks.clear()
        await query.edit_message_text("⛔ All Predictions Stopped")

    elif data=="admin_active_users":
        await query.edit_message_text(f"🟢 Active Users: {len(active_users)}")

    elif data=="admin_users_count":
        await query.edit_message_text(f"👥 Total Users: {len(user_chats)}")

    elif data=="admin_reset_history":
        history.clear()
        await query.edit_message_text("🗑 History Cleared")

    elif data=="admin_broadcast":
        broadcast_mode=True
        await query.edit_message_text("📢 Broadcast Mode ON\n\nএখন message লিখুন")

    elif data=="admin_ban_user":
        await query.edit_message_text("🚫 Ban করতে লিখুন:\n/ban user_id")

    elif data=="admin_stats":
        await query.edit_message_text(f"""📊 BOT STATS
👥 Users: {len(user_chats)}
🟢 Active: {len(active_users)}
🚫 Banned: {len(banned_users)}
""")

    elif data=="admin_history":
        if history:
            await query.edit_message_text(f"📜 Last 10 signals: {', '.join(history[-10:])}")
        else:
            await query.edit_message_text("📜 History is empty")

# ================= BROADCAST =================
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_mode
    if update.effective_user.id != ADMIN_ID:
        return
    if not broadcast_mode:
        return
    msg=update.message.text
    sent=0
    for uid,chat_id in user_chats.items():
        try:
            await safe_send_message(context.bot,chat_id,msg)
            sent+=1
        except:
            pass
    broadcast_mode=False
    await update.message.reply_text(f"📢 Broadcast sent to {sent} users")

# ================= MAIN =================
def main():
    load_users()
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CallbackQueryHandler(button,pattern="join_clicked|confirm_join"))
    app.add_handler(CallbackQueryHandler(admin_button,pattern="admin_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,broadcast_message))
    print("Bot Running...")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()import asyncio
import random
import json
import os
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import NetworkError

# ================= CONFIG =================
BOT_TOKEN = "8646973563:AAE2S3pJ5ZVf35CX6C8uYswwnxUKXJjc6JI"
CHANNEL_LINK = "https://t.me/+aeSXW9qJ7sxiNzg1"
REGISTER_LINK = "https://dkwin9.com/#/register?invitationCode=464381403476"
ADMIN_ID = 6104907925

# ================= DATABASE =================
DATA_FILE = "users.json"

# ================= GLOBALS =================
history = []
active_users = set()
banned_users = set()
user_chats = {}
pending_join_request = set()
running_tasks = {}
broadcast_mode = False

# ================= SAVE / LOAD USERS =================
def save_users():
    data = {"users": list(user_chats.items())}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def load_users():
    global user_chats
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data = json.load(f)
            user_chats = {int(k): v for k, v in data["users"]}

# ================= SAFE SEND =================
async def safe_send_message(bot, chat_id, text, **kwargs):
    for _ in range(3):
        try:
            await bot.send_message(chat_id, text, **kwargs)
            return
        except NetworkError:
            await asyncio.sleep(3)

# ================= PERIOD =================
def generate_period():
    now = datetime.now(timezone.utc)
    year = now.year
    month = f"{now.month:02d}"
    day = f"{now.day:02d}"
    minutes = now.hour * 60 + now.minute
    return f"{year}{month}{day}1000{10001 + minutes}"

# ================= SAME PREDICTION SYSTEM =================
def get_prediction():
    now = datetime.now(timezone.utc)
    seed = now.hour * 60 + now.minute
    random.seed(seed)
    number = random.randint(0,9)
    bigSmall = "BIG" if number >=5 else "SMALL"
    return number,bigSmall

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 JOIN CHANNEL", callback_data="join_clicked")],
        [InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join")]
    ]
    await update.message.reply_text(
        "⚠️ Channel এ Join Request দিন তারপর Confirm চাপুন",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON =================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # JOIN BUTTON
    if query.data == "join_clicked":
        pending_join_request.add(user_id)
        keyboard = [
            [InlineKeyboardButton("📢 OPEN CHANNEL", url=CHANNEL_LINK)],
            [InlineKeyboardButton("✅ CONFIRM", callback_data="confirm_join")]
        ]
        await query.edit_message_text(
            "📢 Channel এ Join / Join Request দিন\nতারপর Confirm চাপুন",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # CONFIRM BUTTON
    elif query.data == "confirm_join":
        # Already running
        if user_id in running_tasks:
            await query.answer("Prediction already running", show_alert=True)
            return

        # Check new user join request or old member
        if user_id not in pending_join_request:
            try:
                member = await context.bot.get_chat_member(CHANNEL_LINK, user_id)
                if member.status not in ["member","administrator","creator"]:
                    await query.answer("❌ আগে Channel এ Join / Join Request দিন", show_alert=True)
                    return
            except:
                await query.answer("❌ আগে Channel এ Join / Join Request দিন", show_alert=True)
                return

        # Prediction start
        active_users.add(user_id)
        user_chats[user_id] = query.message.chat.id
        pending_join_request.discard(user_id)
        save_users()

        # Remove all buttons and text
        await query.edit_message_text("🤖 Predictor Started", reply_markup=None)

        task = asyncio.create_task(auto_predict(query.message.chat.id, context, user_id))
        running_tasks[user_id] = task

# ================= AUTO PREDICT =================
async def auto_predict(chat_id, context, user_id):
    while user_id in active_users:
        now = datetime.now(timezone.utc)
        # Calculate exact next minute start
        next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
        wait_seconds = (next_minute - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        period = generate_period()
        number, bigSmall = get_prediction()
        history.append(bigSmall)
        if len(history) > 10:
            history.pop(0)

        # Send checking message at exact minute start
        try:
            await safe_send_message(context.bot, chat_id, "🚨 Checking New Signal......🚨")
        except Exception as e:
            print(f"Error sending checking message: {e}")

        # 2 seconds delay before prediction
        await asyncio.sleep(2)

        msg = f"""🎯 Dk win & Hgnice 1-Minute AI Signal 🎯

🕹️ PERIOD: {period}
🔎 Result: {bigSmall} | Number: {number}

👨 Creator:- @PARTHO_THE_ONExx"""
        keyboard = [[InlineKeyboardButton("📝 Click Here To Register", url=REGISTER_LINK)]]
        try:
            await safe_send_message(context.bot, chat_id, msg, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            print(f"Error sending prediction message: {e}")

# ================= ADMIN PANEL =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("🚀 Start All", callback_data="admin_start_all"),
         InlineKeyboardButton("⛔ Stop All", callback_data="admin_stop_all")],

        [InlineKeyboardButton("📊 Active Users", callback_data="admin_active_users"),
         InlineKeyboardButton("👥 Users Count", callback_data="admin_users_count")],

        [InlineKeyboardButton("🗑 Reset History", callback_data="admin_reset_history"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],

        [InlineKeyboardButton("🚫 Ban User", callback_data="admin_ban_user"),
         InlineKeyboardButton("📈 Stats", callback_data="admin_stats")],

        [InlineKeyboardButton("📜 History", callback_data="admin_history")]
    ]
    await update.message.reply_text("👑 ADMIN PANEL", reply_markup=InlineKeyboardMarkup(keyboard))

# ================= ADMIN BUTTON =================
async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_mode
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        return
    data=query.data

    if data=="admin_start_all":
        for uid,chat_id in user_chats.items():
            active_users.add(uid)
            if uid not in running_tasks:
                task=asyncio.create_task(auto_predict(chat_id,context,uid))
                running_tasks[uid]=task
        await query.edit_message_text("✅ All Predictions Started")

    elif data=="admin_stop_all":
        active_users.clear()
        for task in running_tasks.values():
            task.cancel()
        running_tasks.clear()
        await query.edit_message_text("⛔ All Predictions Stopped")

    elif data=="admin_active_users":
        await query.edit_message_text(f"🟢 Active Users: {len(active_users)}")

    elif data=="admin_users_count":
        await query.edit_message_text(f"👥 Total Users: {len(user_chats)}")

    elif data=="admin_reset_history":
        history.clear()
        await query.edit_message_text("🗑 History Cleared")

    elif data=="admin_broadcast":
        broadcast_mode=True
        await query.edit_message_text("📢 Broadcast Mode ON\n\nএখন message লিখুন")

    elif data=="admin_ban_user":
        await query.edit_message_text("🚫 Ban করতে লিখুন:\n/ban user_id")

    elif data=="admin_stats":
        await query.edit_message_text(f"""📊 BOT STATS
👥 Users: {len(user_chats)}
🟢 Active: {len(active_users)}
🚫 Banned: {len(banned_users)}
""")

    elif data=="admin_history":
        if history:
            await query.edit_message_text(f"📜 Last 10 signals: {', '.join(history[-10:])}")
        else:
            await query.edit_message_text("📜 History is empty")

# ================= BROADCAST =================
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global broadcast_mode
    if update.effective_user.id != ADMIN_ID:
        return
    if not broadcast_mode:
        return
    msg=update.message.text
    sent=0
    for uid,chat_id in user_chats.items():
        try:
            await safe_send_message(context.bot,chat_id,msg)
            sent+=1
        except:
            pass
    broadcast_mode=False
    await update.message.reply_text(f"📢 Broadcast sent to {sent} users")

# ================= MAIN =================
def main():
    load_users()
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("admin",admin))
    app.add_handler(CallbackQueryHandler(button,pattern="join_clicked|confirm_join"))
    app.add_handler(CallbackQueryHandler(admin_button,pattern="admin_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,broadcast_message))
    print("Bot Running...")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
