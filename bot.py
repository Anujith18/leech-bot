import os
import time
import asyncio
import logging
import aiohttp
import random
import string
import libtorrent as lt
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import UserNotParticipant, MessageNotModified, RPCError

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)

# --- Configuration & Credentials ---
API_ID = int(os.environ.get("API_ID", "1234567"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
ALLOWED_GROUP_ID = int(os.environ.get("ALLOWED_GROUP_ID", "-1004323616488"))
DATABASE_CHANNEL_ID = int(os.environ.get("DATABASE_CHANNEL_ID", "-1003992928955"))
ADMINS = [1727225499] # നിങ്ങളുടെ ടെലഗ്രാം യൂസർ ഐഡി ഇവിടെ നൽകുക

# Force Subscribe Channel & Group Username/ID
UPDATE_CHANNEL = "Anujith_Official1"  # @ ഇല്ലാതെ അല്ലെങ്കിൽ ഐഡി നൽകുക
LEECH_GROUP = "leechbot18"

# --- Start Command Reactions ---
REACTIONS = ["🤝", "😇", "🤗", "😍", "👍", "😐", "🥰", "🤩", "😱", "🤣", "😘", "👏", "😛", "🎉", "⚡️", "🫡", "🤓", "😎", "🏆", "🔥", "🤭", "🌚", "🆒", "👻", "😁"]

app = Client("AlluTvSerialsBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ഡാറ്റാബേസ് ട്രാക്കിംഗ്
PREMIUM_USERS = {}
REDEM_CODES = {} # { "CODE": {"days": days, "uses": remaining_uses} }
USER_VERIFICATION = {} # { user_id: expiry_timestamp }

def human_bytes(size):
    if not size:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"

def get_progress_bar(percentage):
    completed = int(percentage / 10)
    return "█" * completed + "░" * (10 - completed)

# ==========================================
# FORCE SUBSCRIBE CHECK FUNCTION
# ==========================================
async def is_subscribed(client, user_id):
    if user_id in PREMIUM_USERS and datetime.now() < PREMIUM_USERS[user_id]:
        return True
        
    try:
        user_ch = await client.get_chat_member(UPDATE_CHANNEL, user_id)
        if user_ch.status in ["banned", "left"]:
            return False
    except UserNotParticipant:
        return False
    except Exception as e:
        logging.error(f"F-Sub Check Error (Channel): {e}")
        
    try:
        user_gp = await client.get_chat_member(LEECH_GROUP, user_id)
        if user_gp.status in ["banned", "left"]:
            return False
    except UserNotParticipant:
        return False
    except Exception as e:
        logging.error(f"F-Sub Check Error (Group): {e}")
        
    return True

# ==========================================
# START COMMAND HANDLER WITH IMAGE & BUTTONS
# ==========================================
@app.on_message(filters.command(["start"]))
async def start_command(client, message):
    user = message.from_user
    user_name = user.first_name if user else "User"
    
    welcome_caption = (
        f"HEY 🪡™ {user_name} 🤗 Welcome To Anujith Leech bot 👋\n\n"
        f"🤖 I am Leech Bot!\n"
        f"Ready to help you download and manage files. 🥰"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Update Channel Join Now", url="https://t.me/Anujith_Official1")],
        [InlineKeyboardButton("👥 Leech Group Join Now", url="https://t.me/leechbot18")],
        [InlineKeyboardButton("👤 Admin Contact", url="https://t.me/Anujith1238")]
    ])
    
    try:
        await message.reply_photo(
            photo="https://files.catbox.moe/9uc2wn.jpg",
            caption=welcome_caption,
            reply_markup=keyboard
        )
    except Exception as e:
        logging.error(f"Start Image Error: {e}")
        try:
            await message.reply_text(
                welcome_caption,
                reply_markup=keyboard
            )
        except Exception as err:
            logging.error(f"Start Text Error: {err}")

# ==========================================
# BACKGROUND TASK TO CHECK EXPIRED PLANS
# ==========================================
async def check_expired_plans():
    while True:
        await asyncio.sleep(60)
        now = datetime.now()
        expired_users = []
        
        for user_id, expiry_date in PREMIUM_USERS.items():
            if now >= expiry_date:
                expired_users.append(user_id)
                
        for user_id in expired_users:
            del PREMIUM_USERS[user_id]
            try:
                await app.send_message(
                    DATABASE_CHANNEL_ID,
                    f"⚠️ **Premium Plan Expired & Removed!**\n\n"
                    f"🆔 **User ID:** `{user_id}`\n"
                    f"⏰ **Time:** `{now.strftime('%Y-%m-%d %H:%M:%S')}`"
                )
            except Exception as e:
                logging.error(f"Error sending expiration notice: {e}")

# ==========================================
# PREMIUM & REDEEM COMMANDS
# ==========================================
@app.on_message(filters.command(["add_premium", "addplan"]) & filters.user(ADMINS))
async def add_premium(client, message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply_text("⚠️ **Usage:**\n`/add_premium USER_ID DAYS`")
        return
    try:
        user_id = int(args[1])
        days = int(args[2])
        expiry_date = datetime.now() + timedelta(days=days)
        PREMIUM_USERS[user_id] = expiry_date
        await message.reply_text(f"✅ Successfully added user `{user_id}` to **Premium** for {days} days!")
        try:
            await client.send_message(user_id, f"🎉 **You are now a Premium User for {days} Days!**")
        except:
            pass
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command(["remove_premium"]) & filters.user(ADMINS))
async def remove_premium(client, message):
    args = message.text.split()
    if len(args) < 2:
        return
    try:
        user_id = int(args[1])
        if user_id in PREMIUM_USERS:
            del PREMIUM_USERS[user_id]
            await message.reply_text(f"✅ Removed user `{user_id}` from Premium.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command(["createcode"]) & filters.user(ADMINS))
async def create_code(client, message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply_text("⚠️ **Usage:** `/createcode days uses`")
        return
    try:
        days = int(args[1])
        uses = int(args[2])
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        code = f"Anujith-{random_str}"
        REDEM_CODES[code] = {"days": days, "uses": uses}
        await message.reply_text(f"✅ Code Created: `{code}` ({days} Days, {uses} uses)")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command(["redeem"]))
async def redeem_code(client, message):
    user = message.from_user
    if not user:
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("⚠️ **Usage:** `/redeem CODE`")
        return
    code = args[1].strip()
    user_id = user.id
    
    if code not in REDEM_CODES:
        await message.reply_text("❌ **Invalid or Expired Code!**")
        return
        
    code_data = REDEM_CODES[code]
    days = code_data["days"]
    now = datetime.now()
    
    if user_id in PREMIUM_USERS and PREMIUM_USERS[user_id] > now:
        expiry_date = PREMIUM_USERS[user_id] + timedelta(days=days)
    else:
        expiry_date = now + timedelta(days=days)
        
    PREMIUM_USERS[user_id] = expiry_date
    code_data["uses"] -= 1
    if code_data["uses"] <= 0:
        del REDEM_CODES[code]
        
    await message.reply_text(f"🎉 **Code Redeemed Successfully!**\n📅 Expiry: `{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}`")

@app.on_message(filters.command(["myplan", "plan"]))
async def check_my_plan(client, message):
    user = message.from_user
    if not user:
        return
    user_id = user.id
    plans_info = (
        "🤖 **ALLU TV SERIALS - PREMIUM PLANS** 🤖\n\n"
        "💸 ᴘʟᴀɴ ᴘʀɪᴄᴇ ➛ 10₹ - ⏰ 1 ᴅᴀʏꜱ\n"
        "💸 ᴘʟᴀɴ ᴘʀɪᴄᴇ ➛ 25₹ - ⏰ 3 ᴅᴀʏꜱ\n"
        "💸 ᴘʟᴀɴ ᴘʀɪᴄᴇ ➛ 39₹ - ⏰ 1 ᴡᴇᴇᴋ\n"
        "💸 ᴘʟᴀɴ ᴘʀɪᴄᴇ ➛ 89₹ - ⏰ 1 ᴍᴏɴᴛʜ\n\n"
        "✨ Payment UPI ID -\n`vijayalakshmik8825@ybl`\n\n"
        "Send Payment Screenshot 👇\n@Anujith1238\n\n"
        "----------------------------------\n"
    )
    if user_id in PREMIUM_USERS and datetime.now() < PREMIUM_USERS[user_id]:
        expiry_date = PREMIUM_USERS[user_id]
        user_status = f"💎 **Status:** `Active Premium`\n📅 **Expiry:** `{expiry_date.strftime('%Y-%m-%d %H:%M:%S')}`"
    else:
        user_status = "🔸 **Status:** `Free User`"
    await message.reply_text(plans_info + user_status)

# ==========================================
# DOWNLOAD HELPERS (Gofile, Magnet, Telegram)
# ==========================================
async def get_gofile_direct_link(url):
    try:
        file_id = url.split('/')[-1].split('?')[0]
        api_url = f"https://api.gofile.io/contents/{file_id}?wt=4fd6sg3d7s"
        headers = {'User-Agent': 'Mozilla/5.0'}
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, headers=headers) as resp:
                if resp.status == 200:
                    res_json = await resp.json()
                    if res_json.get('status') == 'ok':
                        contents = res_json['data']['contents']
                        for _, item in contents.items():
                            if item['type'] == 'file':
                                return item.get('link')
    except Exception as e:
        logging.error(f"GoFile Error: {e}")
    return None

async def handle_gofile(client, message, status_msg, url):
    try:
        await status_msg.edit_text("📥 **Gofile Link Detected!** Fetching direct link...")
    except MessageNotModified:
        pass
    except Exception:
        pass

    direct_link = await get_gofile_direct_link(url)
    if not direct_link:
        try:
            await status_msg.edit_text("❌ Failed to fetch direct link from Gofile.")
        except:
            pass
        return

    user = message.from_user
    file_path = os.path.join("downloads", f"gofile_{int(time.time())}.mp4")
    os.makedirs("downloads", exist_ok=True)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(direct_link) as resp:
                if resp.status == 200:
                    with open(file_path, "wb") as f:
                        while chunk := await resp.content.read(1024 * 1024):
                            f.write(chunk)
                    
                    try:
                        await status_msg.edit_text("📤 Uploading file to Telegram...")
                    except:
                        pass

                    sent_msg = await client.send_document(
                        chat_id=message.chat.id,
                        document=file_path,
                        caption=f"<b>Gofile File</b>\n👤 <b>User:</b> {user.first_name if user else 'User'}"
                    )
                    try:
                        await sent_msg.copy(chat_id=DATABASE_CHANNEL_ID)
                    except:
                        pass
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    try:
                        await status_msg.delete()
                    except:
                        pass
                    return
    except Exception as e:
        logging.error(f"Gofile download error: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        try:
            await status_msg.edit_text("❌ Download failed.")
        except:
            pass

async def handle_magnet(client, message, status_msg, magnet_link):
    user = message.from_user
    save_path = "downloads"
    os.makedirs(save_path, exist_ok=True)
    ses = lt.session()
    ses.listen_port(6881, 6891)
    params = {'save_path': save_path, 'storage_mode': lt.storage_mode_t.storage_mode_sparse}
    try:
        handle = lt.add_magnet_uri(ses, magnet_link, params)
        handle.set_sequential_download(True)
        try:
            await status_msg.edit_text("⏳ Fetching torrent metadata from peers...")
        except:
            pass

        timeout = 90
        start_time = time.time()
        while not handle.has_metadata():
            if time.time() - start_time > timeout:
                raise Exception("Timeout reached! Poor seeders/peers.")
            await asyncio.sleep(1)
            
        torrent_name = handle.name()
        try:
            await status_msg.edit_text(f"📥 **Downloading Torrent:**\n`{torrent_name}`")
        except:
            pass

        while handle.status().state != lt.torrent_status.seeding:
            s = handle.status()
            percentage = s.progress * 100
            bar = get_progress_bar(percentage)
            progress_str = f"🧲 **Downloading...**\n`{torrent_name}`\n{bar} {percentage:.1f}%\n💾 {human_bytes(s.total_wanted)}"
            try:
                await status_msg.edit_text(progress_str)
            except MessageNotModified:
                pass
            except Exception:
                pass
            await asyncio.sleep(3)

        downloaded_file_path = os.path.join(save_path, torrent_name)
        if not os.path.exists(downloaded_file_path):
            raise Exception("Downloaded path not found.")

        file_size = os.path.getsize(downloaded_file_path) if os.path.isfile(downloaded_file_path) else sum(os.path.getsize(os.path.join(p, f)) for p, _, files in os.walk(downloaded_file_path) for f in files)
        caption = f"<b>{torrent_name}</b>\n👤 <b>By:</b> {user.first_name if user else 'User'}\n📦 <b>Size:</b> {human_bytes(file_size)}"
        
        try:
            await status_msg.edit_text("📤 Uploading torrent file...")
        except:
            pass

        if os.path.isfile(downloaded_file_path):
            sent_msg = await client.send_document(chat_id=message.chat.id, document=downloaded_file_path, caption=caption)
            try:
                await sent_msg.copy(chat_id=DATABASE_CHANNEL_ID)
            except:
                pass
            os.remove(downloaded_file_path)
        else:
            await client.send_message(message.chat.id, f"✅ Completed: `{torrent_name}`")
        
        try:
            await status_msg.delete()
        except:
            pass
    except Exception as e:
        try:
            await status_msg.edit_text(f"❌ **Magnet Failed:** `{str(e)}`")
        except:
            pass

async def handle_telegram_link(client, message, status_msg, link):
    try:
        if "t.me/c/" in link:
            parts = link.split("/c/")
            sub_parts = parts[1].split("/")
            chat_id = int("-100" + sub_parts[0])
            msg_id = int(sub_parts[1].split("?")[0])
        else:
            parts = link.split("t.me/")
            sub_parts = parts[1].split("/")
            chat_id = sub_parts[0]
            msg_id = int(sub_parts[1].split("?")[0])
            
        target_msg = await client.get_messages(chat_id, msg_id)
        if not target_msg or not target_msg.media:
            try:
                await status_msg.edit_text("❌ No media found in link!")
            except:
                pass
            return
            
        try:
            await status_msg.edit_text("📥 Downloading media...")
        except:
            pass

        start_time = time.time()
        downloaded_file = await target_msg.download(
            file_name="downloads/",
            progress=progress_for_telegram,
            progress_args=(client, status_msg, "📥 **Downloading:**", start_time)
        )
        
        try:
            await status_msg.edit_text("📤 Uploading media...")
        except:
            pass

        user = message.from_user
        sent_msg = await client.send_document(
            chat_id=message.chat.id,
            document=downloaded_file,
            caption=f"<b>Leeched Media</b>\n👤 <b>By:</b> {user.first_name if user else 'User'}"
        )
        try:
            await sent_msg.copy(chat_id=DATABASE_CHANNEL_ID)
        except:
            pass
            
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)
            
        try:
            await status_msg.delete()
        except:
            pass
    except Exception as e:
        try:
            await status_msg.edit_text(f"❌ **Telegram Leech Failed:** `{str(e)}`")
        except:
            pass

async def progress_for_telegram(current, total, client, status_msg, text, start_time):
    now = time.time()
    diff = now - start_time
    if round(diff % 5.0) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff if diff > 0 else 0
        progress_str = f"{text}\n{get_progress_bar(percentage)} {percentage:.1f}%\n🚀 {human_bytes(speed)}/s"
        try:
            await status_msg.edit_text(progress_str)
        except MessageNotModified:
            pass
        except Exception:
            pass

# ==========================================
# CALLBACK QUERY HANDLER (TRY AGAIN & VERIFY)
# ==========================================
@app.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    user = callback_query.from_user
    user_id = user.id

    if data == "check_fsub":
        joined = await is_subscribed(client, user_id)
        if joined:
            try:
                await callback_query.message.edit_text(
                    "✅ **Thank you for joining!**\n\n"
                    "You have successfully joined the channel and group. Now you can send your download link again in the group!"
                )
            except:
                pass
        else:
            try:
                await callback_query.answer(
                    "❌ You haven't joined both the channel and group yet! Please join them first.",
                    show_alert=True
                )
            except:
                pass

    elif data == "verify_user":
        expiry_time = time.time() + (12 * 3600)
        USER_VERIFICATION[user_id] = expiry_time
        
        try:
            await callback_query.message.edit_text(
                "✅ **Verification Successful!** 🎉\n\n"
                "You are now verified for the next **12 Hours**. You can now send your links to download files without interruption!"
            )
        except:
            pass

# ==========================================
# MAIN AUTO-DOWNLOAD & F-SUB & 12H VERIFY HANDLER
# ==========================================
@app.on_message(filters.chat(ALLOWED_GROUP_ID) & (filters.text | filters.caption))
async def auto_react_and_leech(client: Client, message: Message):
    text = message.text or message.caption
    if not text or text.startswith("/"):
        return

    if "magnet:?xt=" in text or "gofile.io/d/" in text or "t.me/" in text:
        user = message.from_user
        if not user:
            return
        user_id = user.id

        # 1. Force Subscribe Check with "Try Again" Button
        joined = await is_subscribed(client, user_id)
        if not joined:
            fsub_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Update Channel Join Now", url="https://t.me/Anujith_Official1")],
                [InlineKeyboardButton("👥 Leech Group Join Now", url="https://t.me/leechbot18")],
                [InlineKeyboardButton("🔄 Try Again", callback_data="check_fsub")]
            ])
            try:
                await message.reply_text(
                    f"⚠️ **Hello {user.first_name}!**\n\n"
                    f"You must join our **Update Channel** and **Leech Group** to use this bot!\n\n"
                    f"Please join both and click **'Try Again'** below.",
                    reply_markup=fsub_keyboard
                )
            except Exception as e:
                logging.error(f"F-sub message reply error: {e}")
            return

        # 2. 12 Hours Verification Check (പ്രീമിയം യൂസർമാർക്ക് ബാധകമല്ല)
        is_premium = user_id in PREMIUM_USERS and datetime.now() < PREMIUM_USERS[user_id]
        if not is_premium:
            current_time = time.time()
            if user_id not in USER_VERIFICATION or current_time > USER_VERIFICATION[user_id]:
                verify_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔗 Verify Now (12 Hours)", callback_data="verify_user")]
                ])
                try:
                    await message.reply_text(
                        f"⚠️ **Verification Required!**\n\n"
                        f"Dear {user.first_name}, you haven't verified yet or your 12-hour verification has expired.\n"
                        f"Please click the button below to complete your verification.",
                        reply_markup=verify_keyboard
                    )
                except Exception as e:
                    logging.error(f"Verification message reply error: {e}")
                return

        # 3. ഡൗൺലോഡ് പ്രോസസ്സ് തുടങ്ങുന്നു
        try:
            chosen_emoji = random.choice(REACTIONS)
            await message.react(chosen_emoji)
        except Exception as e:
            logging.error(f"Reaction Error: {e}")
            
        status_msg = await message.reply_text("🔍 **Link detected! Auto-downloading...**")
        
        if "magnet:?xt=" in text:
            await handle_magnet(client, message, status_msg, text)
        elif "gofile.io/d/" in text:
            await handle_gofile(client, message, status_msg, text)
        elif "t.me/" in text:
            await handle_telegram_link(client, message, status_msg, text)

# --- Bot Start Hook ---
@app.on_ready()
async def on_ready(client):
    print(f"Bot started as {client.me.username}")
    asyncio.create_task(check_expired_plans())

# --- Run Bot ---
if __name__ == "__main__":
    app.run()
