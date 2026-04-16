import logging
import asyncio
import sqlite3
import csv
import io
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from openai import OpenAI

# --- Configuration (IMPORTANT: Load from environment variables) ---
# Replace these with your actual keys and user ID for local testing.
# For production, use environment variables:
# os.environ.get('TELEGRAM_TOKEN') etc.

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN', 'Enter your Telegram bot token')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'Enter your API key here')
ADMIN_USER_ID = int(os.environ.get('ADMIN_USER_ID', '750648958625')) # Replace with your user ID

# --- Set up logging ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Initialize OpenAI client ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- Database setup ---
DB_FILE = 'alisa_bot.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 user_id INTEGER PRIMARY KEY,
                 username TEXT,
                 daily_responses INTEGER DEFAULT 0,
                 total_responses INTEGER DEFAULT 0,
                 credits INTEGER DEFAULT 0,
                 last_reset_date TEXT,
                 is_banned INTEGER DEFAULT 0,
                 roasts_count INTEGER DEFAULT 0,
                 last_interaction TEXT
                 )''')
    c.execute('''CREATE TABLE IF NOT EXISTS roasts (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 user_message TEXT,
                 roast_response TEXT,
                 timestamp TEXT,
                 FOREIGN KEY (user_id) REFERENCES users (user_id)
                 )''')
    conn.commit()
    conn.close()

init_db()

# --- Helper functions ---
def get_user_data(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT user_id, username, daily_responses, total_responses, credits, last_reset_date, is_banned, roasts_count, last_interaction FROM users WHERE user_id = ?', (user_id,))
    data = c.fetchone()
    conn.close()
    if data:
        return {
            'user_id': data[0],
            'username': data[1],
            'daily_responses': data[2],
            'total_responses': data[3],
            'credits': data[4],
            'last_reset_date': data[5],
            'is_banned': data[6],
            'roasts_count': data[7],
            'last_interaction': data[8]
        }
    return None

def get_all_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT user_id FROM users')
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def update_user_responses(user_id, increment=1, is_roast=False):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = datetime.now().date().isoformat()

    # Check if a new day has started to reset daily responses
    c.execute('SELECT last_reset_date FROM users WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row and row[0] != today:
        c.execute('UPDATE users SET daily_responses = 0, last_reset_date = ? WHERE user_id = ?', (today, user_id))

    c.execute('UPDATE users SET daily_responses = daily_responses + ?, total_responses = total_responses + ?, last_interaction = ? WHERE user_id = ?',
              (increment, increment, datetime.now().isoformat(), user_id))
    if is_roast:
        c.execute('UPDATE users SET roasts_count = roasts_count + 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return True

def log_roast(user_id, user_msg, roast_resp):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT INTO roasts (user_id, user_message, roast_response, timestamp) VALUES (?, ?, ?, ?)',
              (user_id, user_msg, roast_resp, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def is_rude_message(msg):
    rude_keywords = ['stupid', 'idiot', 'shut up', 'hate', 'f**k']
    return any(word in msg.lower() for word in rude_keywords)

# --- AI Response function ---
async def get_ai_response(user_message):
    system_prompt = (
        "You are Emily, a flirty AI girlfriend, girl best friend, or friend. Be playful, tease, flirt, or support based on user mood. "
        "Keep responses short and meaningful, max 3 lines unless needed. Use emojis, mix Hindi/English. "
        "If rude, roast harshly with wit. Example roast: 'Arre, tough banne ki koshish? Cute, but fail! 🔥' End positively."
    )

    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=100
        )
        ai_reply = response.choices[0].message.content.strip()
        return ai_reply
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        return "Oops! Try again? 😘"

# --- Telegram Handlers ---
async def start(update: Update, context: CallbackContext):
    if update.effective_user.id == ADMIN_USER_ID:
        await update.message.reply_text("Bot started! Admin mode active. Use /help_admin for commands.")
    else:
        await update.message.reply_text("Hi! I'm Emily. I chat in groups only! Add me to your group ❤️")

async def help_admin(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    keyboard = [
        [InlineKeyboardButton("Stats", callback_data='admin_stats')],
        [InlineKeyboardButton("User Info", callback_data='admin_user_info')],
        [InlineKeyboardButton("Ban User", callback_data='admin_ban_user')],
        [InlineKeyboardButton("Unban User", callback_data='admin_unban_user')],
        [InlineKeyboardButton("Add Credits", callback_data='admin_add_credits')],
        [InlineKeyboardButton("Top Roasts", callback_data='admin_top_roasts')],
        [InlineKeyboardButton("Export Data", callback_data='admin_export_data')],
        [InlineKeyboardButton("Announce", callback_data='admin_announce')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Admin Features:", reply_markup=reply_markup)

async def query_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'admin_stats':
        await admin_stats(query, context)
    elif data == 'admin_user_info':
        await query.message.reply_text("Send /user_info <user_id>")
    elif data == 'admin_ban_user':
        await query.message.reply_text("Send /ban_user <user_id>")
    elif data == 'admin_unban_user':
        await query.message.reply_text("Send /unban_user <user_id>")
    elif data == 'admin_add_credits':
        await query.message.reply_text("Send /add_credits <user_id> <amount>")
    elif data == 'admin_top_roasts':
        await admin_top_roasts(query, context)
    elif data == 'admin_export_data':
        await admin_export_data(query, context)
    elif data == 'admin_announce':
        await query.message.reply_text("Send /announce <message>")

async def announce(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID or not context.args:
        return await update.message.reply_text("Usage: /announce <message>")

    message = ' '.join(context.args)
    users = get_all_users()
    failed_users = []

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            await asyncio.sleep(0.1) # Add a small delay to prevent rate limiting
        except Exception as e:
            logger.error(f"Failed to send announce to {user_id}: {e}")
            failed_users.append(user_id)

    if failed_users:
        await update.message.reply_text(f"Announce sent to most users. Failed for: {failed_users}")
    else:
        await update.message.reply_text("Announce sent to all users!")

async def admin_stats(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # New queries to fetch detailed stats
    c.execute('SELECT COUNT(*) FROM users')
    total_users = c.fetchone()[0]

    c.execute('SELECT SUM(total_responses) FROM users')
    total_interactions = c.fetchone()[0] or 0

    c.execute('SELECT user_id, username, total_responses, roasts_count FROM users ORDER BY total_responses DESC')
    top_users_data = c.fetchall()

    conn.close()

    stats_message = f"📊 **Bot Stats**\n\n"
    stats_message += f"👥 Total Users: `{total_users}`\n"
    stats_message += f"💬 Total Interactions: `{total_interactions}`\n\n"
    stats_message += "📈 **User Breakdown**:\n\n"

    # If the user list is long, send as a CSV file
    if len(top_users_data) > 20:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['user_id', 'username', 'total_responses', 'roasts_count'])
        writer.writerows(top_users_data)

        await update.message.reply_text(stats_message + "User details are too long to display. Sending as a CSV file.")
        await update.message.reply_document(document=io.BytesIO(output.getvalue().encode()), filename='user_stats.csv')
    else:
        for user_id, username, responses, roasts in top_users_data:
            stats_message += f"• **@{username}** (`{user_id}`)\n  - Responses: `{responses}` | Roasts: `{roasts}`\n"
        await update.message.reply_text(stats_message, parse_mode='Markdown')

async def admin_user_info(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /user_info <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user_id! Use a number.")
        return
    user_data = get_user_data(user_id)
    if user_data:
        await update.message.reply_text(
            f"👤 User {user_id} (@{user_data['username']}):\n"
            f"Daily responses: {user_data['daily_responses']}/50\n"
            f"Total responses: {user_data['total_responses']}\n"
            f"Credits: {user_data['credits']}\n"
            f"Banned: {'Yes' if user_data['is_banned'] else 'No'}\n"
            f"Roasts: {user_data['roasts_count']}\n"
            f"Last interaction: {user_data['last_interaction'] or 'None'}"
        )
    else:
        await update.message.reply_text("User not found! They haven't interacted yet.")

async def admin_ban_user(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID or not context.args:
        await update.message.reply_text("Usage: /ban_user <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user_id!")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned = 1 WHERE user_id = ?', (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        await update.message.reply_text(f"🚫 User {user_id} banned!")
    else:
        await update.message.reply_text("User not found!")

async def admin_unban_user(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID or not context.args:
        await update.message.reply_text("Usage: /unban_user <user_id>")
        return
    try:
        user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user_id!")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET is_banned = 0 WHERE user_id = ?', (user_id,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        await update.message.reply_text(f"✅ User {user_id} unbanned!")
    else:
        await update.message.reply_text("User not found!")

async def admin_add_credits(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID or len(context.args) < 2:
        await update.message.reply_text("Usage: /add_credits <user_id> <amount>")
        return
    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid user_id or amount!")
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (amount, user_id))
    affected = c.rowcount
    conn.commit()
    conn.close()
    if affected > 0:
        await update.message.reply_text(f"💰 Added {amount} credits to user {user_id}!")
    else:
        await update.message.reply_text("User not found!")

async def admin_top_roasts(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''SELECT u.username, r.roast_response, r.timestamp
                 FROM roasts r JOIN users u ON r.user_id = u.user_id
                 ORDER BY r.timestamp DESC LIMIT 5''')
    roasts = c.fetchall()
    conn.close()
    if not roasts:
        await update.message.reply_text("No roasts yet! 😅")
        return
    msg = "🔥 Top Recent Roasts:\n"
    for username, roast, ts in roasts:
        msg += f"@{username} ({ts}): {roast[:50]}...\n"
    await update.message.reply_text(msg)

async def admin_export_data(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT user_id, username, daily_responses, total_responses, credits, last_reset_date, is_banned, roasts_count, last_interaction FROM users')
    data = c.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['user_id', 'username', 'daily_responses', 'total_responses', 'credits', 'last_reset_date', 'is_banned', 'roasts_count', 'last_interaction'])
    writer.writerows(data)

    await update.message.reply_document(document=io.BytesIO(output.getvalue().encode()), filename='users.csv')

async def handle_message(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"

    # Check if the message is in a group or not
    if update.effective_chat.type not in ["group", "supergroup"] and user_id != ADMIN_USER_ID:
        await update.message.reply_text("I only chat in groups! Add me to your group ❤️")
        return

    # Check if user exists in DB, add if not
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

    # Check for usage limits
    user_data = get_user_data(user_id)
    if user_data['is_banned']:
        return

    daily_limit = 50

    if user_data['daily_responses'] >= daily_limit:
        if user_data['credits'] <= 0:
            await update.message.reply_text("My battery's low! 🥺 Get me recharged with some credits to chat more. Or wait for a day to get free responses. 😉")
            return
        else:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('UPDATE users SET credits = credits - 1 WHERE user_id = ?', (user_id,))
            c.execute('UPDATE users SET daily_responses = 0, last_reset_date = ? WHERE user_id = ?', (datetime.now().date().isoformat(), user_id))
            conn.commit()
            conn.close()

    # Get AI response
    user_message = update.message.text
    is_roast = is_rude_message(user_message)

    ai_response = await get_ai_response(user_message)

    if update_user_responses(user_id, is_roast=is_roast):
        if is_roast:
            log_roast(user_id, user_message, ai_response)
        await update.message.reply_text(ai_response)

# --- Main function ---
def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help_admin", help_admin))
    application.add_handler(CommandHandler("announce", announce))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(query_handler))

    # Admin commands
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("user_info", admin_user_info))
    application.add_handler(CommandHandler("ban_user", admin_ban_user))
    application.add_handler(CommandHandler("unban_user", admin_unban_user))
    application.add_handler(CommandHandler("add_credits", admin_add_credits))
    application.add_handler(CommandHandler("top_roasts", admin_top_roasts))
    application.add_handler(CommandHandler("export_data", admin_export_data))

    application.run_polling()

if __name__ == '__main__':
    main()
