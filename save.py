import telethon
from telethon import TelegramClient, events, Button
import re
import asyncio
from datetime import datetime
import json
import http.server
import socketserver
import threading
import os

# إعداد بيانات الاعتماد الخاصة بك
API_ID =  os.getenv("API_ID")
API_HASH =  os.getenv("API_HASH")
BOT_TOKEN =  os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = '@EREN_PYTHON'  # اسم المستخدم لقناتك

# تعريف المتغيرات العالمية
user_accounts = {}  # معجم لتخزين بيانات المستخدمين
developer_id = int( os.getenv("developer_id"))  # معرف المطور
broadcast_state = {}  # حالة الإذاعة
maintenance_mode = False  # حالة الصيانة
maintenance_message = ""  # الرسالة التي تظهر أثناء الصيانة

# تحميل أو إنشاء ملف المستخدمين
def load_users():
    try:
        with open('users.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data():
    with open('users.json', 'w') as f:
        json.dump(user_accounts, f, ensure_ascii=False, indent=4)

# تحميل بيانات المستخدمين عند بدء التشغيل
user_accounts = load_users()

# إنشاء عميل Telethon
client = TelegramClient('bot_session', API_ID, API_HASH)

# التحقق من اشتراك المستخدم في القناة
async def check_subscription(user_id):
    try:
        participant = await client(telethon.tl.functions.channels.GetParticipantRequest(
            channel=CHANNEL_USERNAME,
            participant=user_id
        ))
        return True
    except telethon.errors.rpcerrorlist.UserNotParticipantError:
        return False

# إرسال رسالة الاشتراك الإجباري
async def send_subscription_prompt(event):
    buttons = [
        [Button.url("⦗ Python tools ⦘", f"https://t.me/{CHANNEL_USERNAME[1:]}")],
        [Button.inline("تحقق", b'verify')]
    ]
    await event.reply(
        "عذرا عزيزي... يجب الإشتراك في قناة البوت الرسمية حتى تتمكن من إستخدام البوت...🙋‍♂\n"
        "إشترك هنا ⏬⏬ ثم إضغط تحقق 👉",
        buttons=buttons
    )

# وظيفة عد تنازلي لتحديث الرسالة كل 10 ثوانٍ
async def countdown(event, info_response, delay, date, views):
    for i in range(delay, 0, -10):
        try:
            await info_response.edit(f"""
            ↯︙تاريخ النشر ↫ ⦗ {date} ⦘
            ↯︙عدد المشاهدات ↫ ⦗ {views} ⦘
            ↯︙سيتم حذف المحتوى بعد ↫ ⦗ {i} ⦘ ثانية
            ↯︙قم بحفظه او اعادة التوجيه
            """, parse_mode='html')
            await asyncio.sleep(10)
        except:
            break  # الخروج إذا حدث خطأ مثل حذف الرسالة بالفعل

# وظيفة لحذف الرسائل بعد فترة معينة
async def delete_messages_later(chat_id, message_ids, delay=60):  
    await asyncio.sleep(delay)
    await client.delete_messages(chat_id, message_ids, revoke=True)

# وظيفة لعرض إحصائيات البوت
async def show_bot_stats(event):
    users = load_users()
    user_count = len(users)
    
    stats_message = f"📊 <b>إحصائيات البوت:</b>\n\n👥 <b>عدد المستخدمين:</b> {user_count}\n\n"
    
    for index, (user_id, user_data) in enumerate(users.items(), start=1):
        # التحقق من وجود البيانات قبل الوصول إليها
        name = user_data.get('name', 'غير معروف')
        username = user_data.get('username', 'بدون يوزر')
        stats_message += f"{index}. {name} (@{username}) - ID: {user_id}\n"
    
    # إضافة زر الرجوع
    buttons = [
        [Button.inline("رجوع ↩️", b'back_to_main')]
    ]
    await event.edit(stats_message, parse_mode='html', buttons=buttons)

# إرسال رسالة الأوامر الخاصة بالمطور
async def send_developer_commands(event):
    buttons = [
        [Button.inline("إذاعة 📢", b'broadcast')],  # زر الإذاعة في الأعلى
        [Button.inline("تفعيل الصيانه", b'enable_maintenance'), Button.inline("إيقاف الصيانه", b'disable_maintenance')],  # زر تفعيل وإيقاف الصيانه بجانب بعضهما
        [Button.inline("📊 إحصائيات البوت", b'stats')]  # زر الإحصائيات في الأسفل
    ]
    await event.reply(
        "<b>• مرحبا عزيزي المطور يمكنك في اوامر البوت الخاص بك عن طريق الازرار التالية 🦾</b>",
        parse_mode='html',
        buttons=buttons
    )

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)  # تحويل إلى نص لضمان الاتساق
    username = sender.username or "بدون يوزر"
    full_name = f"{sender.first_name} {sender.last_name or ''}".strip()

    # التحقق إذا كان المستخدم مسجلًا بالفعل
    if sender_id not in user_accounts:
        # تسجيل المستخدم الجديد مع تخزين الاسم واليوزر
        user_accounts[sender_id] = {
            "name": full_name,
            "username": username,
            "sessions": [],
            "users": []
        }
        save_data()  # حفظ البيانات إلى ملف

        # إرسال رسالة للمطور عند دخول عضو جديد
        total_users = len(user_accounts)  # إجمالي عدد المستخدمين
        message = (
            f"**☑️| انضم عضو جديد**\n"
            f"━━━━━━━━━━━━━\n"
            f"👤 **الاسم:** {full_name}\n"
            f"🔗 **المعرف:** @{username if username != 'بدون يوزر' else 'بدون يوزر'}\n"
            f"🆔 **الآي دي:** `{sender_id}`\n"
            f"━━━━━━━━━━━━━\n"
            f"📊 **إجمالي الأعضاء:** {total_users}\n"
        )
        await client.send_message(developer_id, message)

    # التحقق من اشتراك المستخدم في القناة
    if not await check_subscription(sender.id):
        await send_subscription_prompt(event)
        return

    # التحقق من حالة الصيانة
    global maintenance_mode, maintenance_message
    if maintenance_mode and sender.id != developer_id:
        await event.reply(maintenance_message, parse_mode='html')
        return

    # إرسال رسالة الترحيب إذا كان المستخدم مشتركًا
    if sender.username:
        user_link = f'<a href="https://t.me/{sender.username}">{sender.first_name}</a>'
    else:
        user_link = sender.first_name

    welcome_message = f"""
    ↯︙اهلاً بك عزيزي ↫ ⦗{user_link}⦘
    ↯︙في بوت حفظ المحتوى المقيد.    
    ↯︙ارسل رابط المنشور فقط.          """
    
    buttons = [
        [Button.url("⦗ WORLED EREN ⦘", "https://t.me/ERENYA0")]
    ]
    
    await event.reply(welcome_message, parse_mode='html', buttons=buttons, link_preview=False)

    # إرسال رسالة الأوامر الخاصة بالمطور إذا كان المستخدم مطورًا
    if sender.id == developer_id:
        await send_developer_commands(event)

# التعامل مع الضغط على زر الأوامر الخاصة بالمطور
@client.on(events.CallbackQuery)
async def callback_handler(event):
    global maintenance_mode, maintenance_message
    if event.data == b'stats':
        if event.sender_id == developer_id:
            await show_bot_stats(event)
        else:
            await event.answer("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.", alert=True)
    elif event.data == b'verify':
        if await check_subscription(event.sender_id):
            await event.answer("تم التحقق ✔️", alert=True)
            await event.delete()
            await start(event)
        else:
            await event.answer("❌ لم تشترك في القناة بعد.", alert=True)
    elif event.data == b'broadcast':
        if event.sender_id == developer_id:
            # وضع المستخدم في حالة إذاعة
            broadcast_state[event.chat_id] = True

            # تعديل الرسالة الحالية لعرض النص المطلوب وزر الرجوع
            buttons = [
                [Button.inline("رجوع ↩️", b'back_to_main')]
            ]
            await event.edit(
                "<b>• أرسل الآن الكليشة ( النص أو جميع الوسائط )</b>\n"
                "<b>• يمكنك استخدام كود جاهز في الإذاعة أو يمكنك استخدام الماركدوان</b>",
                parse_mode='html',
                buttons=buttons
            )
        else:
            await event.answer("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.", alert=True)
    elif event.data == b'enable_maintenance':
        if event.sender_id == developer_id:
            # وضع المستخدم في حالة تفعيل الصيانة
            await event.answer("أرسل الآن الرسالة التي تريد أن تظهر للمستخدمين أثناء الصيانة:", alert=True)
            await event.edit(
                "<b>• أرسل الآن الرسالة التي تريد أن تظهر للمستخدمين أثناء الصيانة:</b>",
                parse_mode='html'
            )
            # وضع المستخدم في حالة انتظار الرسالة
            broadcast_state[event.chat_id] = 'waiting_for_maintenance_message'
        else:
            await event.answer("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.", alert=True)
    elif event.data == b'disable_maintenance':
        if event.sender_id == developer_id:
            # إيقاف حالة الصيانة
            maintenance_mode = False
            maintenance_message = ""
            await event.answer("تم إيقاف الصيانة بنجاح ✅", alert=True)
            await send_developer_commands(event)
        else:
            await event.answer("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.", alert=True)
    elif event.data == b'back_to_main':
        if event.sender_id == developer_id:
            # إعادة تعيين حالة الإذاعة
            broadcast_state[event.chat_id] = False

            # إعادة إرسال رسالة الأوامر الخاصة بالمطور في نفس الرسالة
            buttons = [
                [Button.inline("إذاعة 📢", b'broadcast')],
                [Button.inline("تفعيل الصيانه", b'enable_maintenance'), Button.inline("إيقاف الصيانه", b'disable_maintenance')],
                [Button.inline("📊 إحصائيات البوت", b'stats')]
            ]
            await event.edit(
                "<b>• مرحبا عزيزي المطور يمكنك في اوامر البوت الخاص بك عن طريق الازرار التالية 🦾</b>",
                parse_mode='html',
                buttons=buttons
            )
        else:
            await event.answer("❌ ليس لديك صلاحية الوصول إلى هذه الميزة.", alert=True)

# التعامل مع الرسائل أثناء حالة الإذاعة أو الصيانة
@client.on(events.NewMessage())
async def handler(event):
    global maintenance_mode, maintenance_message
    if event.message.message == "/start":
        return

    # التحقق من حالة الصيانة
    if maintenance_mode and event.sender_id != developer_id:
        await event.reply(maintenance_message, parse_mode='html')
        return

    # التحقق من حالة الإذاعة
    if event.chat_id in broadcast_state and broadcast_state[event.chat_id] == 'waiting_for_maintenance_message':
        maintenance_mode = True
        maintenance_message = event.message.message
        await event.reply("<b>تم تفعيل وضع الصيانة بنجاح ✅</b>", parse_mode='html')
        broadcast_state[event.chat_id] = False
        await send_developer_commands(event)
        return

    if event.chat_id in broadcast_state and broadcast_state[event.chat_id]:
        # إرسال الرسالة إلى جميع المستخدمين
        users = load_users()
        for user_id in users:
            try:
                await client.send_message(int(user_id), event.message)
            except Exception as e:
                print(f"Error sending broadcast to user {user_id}: {e}")

        # إعادة تعيين حالة الإذاعة
        broadcast_state[event.chat_id] = False

        # إرسال رسالة تأكيد
        await event.reply("<b>تم إرسال الإذاعة بنجاح ✅</b>", parse_mode='html')

        # إعادة إرسال رسالة الأوامر الخاصة بالمطور
        await send_developer_commands(event)
        return

    # التحقق من اشتراك المستخدم في القناة
    if not await check_subscription(event.sender_id):
        await send_subscription_prompt(event)
        return

    links = event.message.message.strip().split()

    for link in links:
        if not re.match(r'https://t.me/([^/]+)/(\d+)', link):
            await event.reply("⚠️ <b>الرابط غير صالح. تأكد من إدخال رابط من قناة تليجرام.</b>", parse_mode='html')
            continue

        match = re.match(r'https://t.me/([^/]+)/(\d+)', link)
        if match:
            channel_username = match.group(1)
            post_id = match.group(2)

            try:
                post = await client.get_messages(channel_username, ids=int(post_id))
                message_text = post.message
                views = post.views or "غير معروف"
                date = post.date.strftime('%Y-%m-%d %H:%M:%S') if post.date else "تاريخ غير معروف"

                if post.media:
                    message_response = await client.send_file(event.chat_id, post.media, caption=message_text)
                else:
                    message_response = await event.reply(message_text)

                info_message = f"""
                ↯︙تاريخ النشر ↫ ⦗ {date} ⦘
                ↯︙عدد المشاهدات ↫ ⦗ {views} ⦘
                ↯︙سيتم حذف المحتوى بعد ↫ ⦗ 1 ⦘ دقيقة
                ↯︙قم بحفظه او اعادة التوجيه
                """
                info_response = await event.reply(info_message, parse_mode='html')

                asyncio.create_task(countdown(event, info_response, delay=60, date=date, views=views))

                await delete_messages_later(event.chat_id, [event.id, message_response.id, info_response.id], delay=60)

            except telethon.errors.rpcerrorlist.ChannelPrivateError:
                await event.reply("❌ <b>لا يمكن الوصول إلى هذه القناة لأنها خاصة.</b>", parse_mode='html')
            except telethon.errors.rpcerrorlist.MessageIdInvalidError:
                await event.reply("❌ <b>معرف المنشور غير صالح أو تم حذفه.</b>", parse_mode='html')
            except Exception as e:
                await event.reply(f"❌ <b>حدث خطأ غير متوقع:</b> {e}", parse_mode='html')

        else:
            await event.reply("⚠️ <b>يرجى إدخال رابط صحيح لمنشور من قناة مقيدة.</b>", parse_mode='html')
            
def run_server():
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", 8000), handler) as httpd:
        print("Serving on port 8000")
        httpd.serve_forever()

# تشغيل الخادم في خيط جديد
server_thread = threading.Thread(target=run_server)
server_thread.start()	            
            

# بدء تشغيل البوت
while True:
    try:
        client.start(bot_token=BOT_TOKEN)
        print("Bot started successfully")
        client.run_until_disconnected()
    except Exception as e:
        print(f"Error occurred: {e}")
        continue
