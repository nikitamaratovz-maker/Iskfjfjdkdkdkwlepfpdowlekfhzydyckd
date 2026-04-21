import telebot
import sqlite3
import requests
import time
import threading
import random
import string
from telebot import types

# === [ КОНФИГУРАЦИЯ ] ===
BOT_TOKEN = "8710963699:AAFZ8j_ASTp_wMtxgHV2vf_TXazExyTyR60"
BOT_USERNAME = "KrestblMailBot" 
ADMIN_ID = 8727723180
REQUIRED_CHANNEL = "@krectbll"
CHANNEL_LINK = "https://t.me/krectbll"
API_URL = "https://api.mail.tm"
IMG_LINK = "https://i.postimg.cc/50j8fp2c/Picsart-26-04-20-22-01-28-165.jpg"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# === [ БАЗА ДАННЫХ ] ===
def init_db():
    conn = sqlite3.connect('krestbl_v8_final.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                   (user_id INTEGER PRIMARY KEY, mails_left INTEGER DEFAULT 1, 
                    ref_count INTEGER DEFAULT 0, referrer_id INTEGER, is_counted INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_emails 
                   (user_id INTEGER PRIMARY KEY, email TEXT, token TEXT, expiry TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS seen_msgs (msg_id TEXT PRIMARY KEY)''')
    conn.commit()
    return conn

db = init_db()

def is_sub(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def get_user(user_id):
    cursor = db.cursor()
    cursor.execute("SELECT mails_left, ref_count, referrer_id, is_counted FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    if not res:
        # Если юзер почему-то не в базе, создаем его на лету
        cursor.execute("INSERT OR IGNORE INTO users (user_id, mails_left) VALUES (?, 1)", (user_id,))
        db.commit()
        return (1, 0, None, 0)
    return res

def send_layout(chat_id, text, markup=None):
    return bot.send_photo(chat_id, photo=IMG_LINK, caption=text, reply_markup=markup, parse_mode='HTML')

# === [ КЛАВИАТУРЫ ] ===
def main_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("⚡️ Создать почту", "📥 Мои письма")
    markup.add("👤 Профиль", "🔗 Партнерка")
    return markup

def time_kb():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⏱ 1 час", callback_data="settime_1"),
               types.InlineKeyboardButton("⏱ 2 часа", callback_data="settime_2"))
    return markup

# === [ ОБРАБОТЧИКИ ] ===

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    cursor = db.cursor()
    user = get_user(uid)
    
    # Проверка реферальной ссылки
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        rid = int(args[1])
        if rid != uid:
            cursor.execute("UPDATE users SET referrer_id = ? WHERE user_id = ? AND referrer_id IS NULL", (rid, uid))
            db.commit()

    if not is_sub(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➡️ Подписаться на канал", url=CHANNEL_LINK))
        kb.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub"))
        send_layout(message.chat.id, "<b>📍 ДОСТУП ОГРАНИЧЕН</b>\n\nЧтобы использовать генератор и получить <b>+1</b> стартовую попытку, подпишитесь на наш официальный канал.", markup=kb)
        return

    # Начисление бонуса +3
    user = get_user(uid)
    if user[3] == 0: # is_counted
        if user[2]: # referrer_id
            cursor.execute("UPDATE users SET mails_left = mails_left + 3, ref_count = ref_count + 1 WHERE user_id = ?", (user[2],))
            cursor.execute("UPDATE users SET is_counted = 1 WHERE user_id = ?", (uid,))
            db.commit()
            try:
                bot.send_message(user[2], f'<tg-emoji emoji-id="5172834782823842584">🎁</tg-emoji> <b>Новый реферал!</b>\n\nВам начислено <b>+3 создания</b> за подписку вашего друга.', parse_mode='HTML')
            except: pass
        else:
            cursor.execute("UPDATE users SET is_counted = 1 WHERE user_id = ?", (uid,))
            db.commit()

    welcome = (
        f'<tg-emoji emoji-id="5085022089103016925">📩</tg-emoji> <b>KRESTBL MAIL GENERATOR</b>\n\n'
        f'Готов к работе. Выберите действие в меню ниже:'
    )
    send_layout(message.chat.id, welcome, markup=main_kb())

@bot.message_handler(func=lambda m: True)
def text_buttons(message):
    uid = message.from_user.id
    if not is_sub(uid):
        start(message)
        return

    if message.text == "⚡️ Создать почту":
        u = get_user(uid)
        if u[0] <= 0:
            send_layout(message.chat.id, "<b>❌ ЛИМИТ ИСЧЕРПАН</b>\n\nУ вас 0 доступных созданий. Пригласите друга по своей ссылке, чтобы получить <b>+3</b> попытки.")
            return
        send_layout(message.chat.id, f'<tg-emoji emoji-id="5116093437300442328">⏳</tg-emoji> <b>ВРЕМЯ ЖИЗНИ</b>\n\nНа какой срок забронировать почтовый ящик?', markup=time_kb())

    elif message.text == "👤 Профиль":
        u = get_user(uid)
        prof_text = (
            f'<tg-emoji emoji-id="5121007227779416740">👤</tg-emoji> <b>ВАШ АККАУНТ</b>\n'
            f'────────────────────\n'
            f'<tg-emoji emoji-id="5116575178012235794">🆔</tg-emoji> Ваш ID: <code>{uid}</code>\n'
            f'<tg-emoji emoji-id="5116113383128564448">✉️</tg-emoji> Доступно созданий: <b>{u[0]}</b>\n'
            f'<tg-emoji emoji-id="5134104558749877076">👥</tg-emoji> Приглашено друзей: <b>{u[1]}</b>\n'
            f'────────────────────'
        )
        send_layout(message.chat.id, prof_text)

    elif message.text == "🔗 Партнерка":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        ref_text = (
            f'<tg-emoji emoji-id="5134122666331996794">🤝</tg-emoji> <b>ПАРТНЕРСКАЯ ПРОГРАММА</b>\n'
            f'────────────────────\n'
            f'<tg-emoji emoji-id="5172834782823842584">💎</tg-emoji> Награда: <b>+3 создания</b> за друга\n'
            f'<tg-emoji emoji-id="4916086774649848789">🔗</tg-emoji> Ваша ссылка:\n<code>{link}</code>\n'
            f'────────────────────\n'
            f'<i>Бонус начисляется мгновенно после подписки друга на канал.</i>'
        )
        send_layout(message.chat.id, ref_text)

    elif message.text == "📥 Мои письма":
        cursor = db.cursor()
        cursor.execute("SELECT email FROM active_emails WHERE user_id = ?", (uid,))
        res = cursor.fetchone()
        if not res:
            send_layout(message.chat.id, "<b>📭 У вас нет активной почты.</b>\nСоздайте её через меню.")
        else:
            send_layout(message.chat.id, f'<tg-emoji emoji-id="4916036072560919511">📬</tg-emoji> <b>АКТИВНЫЙ АДРЕС:</b>\n<code>{res[0]}</code>\n\nНовые сообщения отобразятся здесь автоматически.')

@bot.callback_query_handler(func=lambda c: True)
def calls(call):
    uid = call.from_user.id
    if call.data == "check_sub":
        if is_sub(uid):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            # Перевызываем старт
            message = call.message
            message.from_user = call.from_user
            message.text = "/start"
            start(message)
        else:
            bot.answer_callback_query(call.id, "❌ Вы не подписаны на канал!", show_alert=True)

    elif call.data.startswith("settime_"):
        u = get_user(uid)
        if u[0] <= 0:
            bot.answer_callback_query(call.id, "❌ Закончились попытки!", show_alert=True)
            return

        h = int(call.data.split("_")[1])
        bot.edit_message_caption("🛰 <b>Генерация защищенного адреса...</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
        
        try:
            dom = requests.get(f"{API_URL}/domains").json()['hydra:member'][0]['domain']
            log = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            addr = f"krest_{log}@{dom}"
            pwd = "pass_" + log
            
            if requests.post(f"{API_URL}/accounts", json={"address": addr, "password": pwd}).status_code == 201:
                tk = requests.post(f"{API_URL}/token", json={"address": addr, "password": pwd}).json()['token']
                ex = time.time() + (h * 3600)
                
                cursor = db.cursor()
                cursor.execute("UPDATE users SET mails_left = mails_left - 1 WHERE user_id = ?", (uid,))
                cursor.execute("REPLACE INTO active_emails (user_id, email, token, expiry) VALUES (?, ?, ?, ?)", (uid, addr, tk, str(ex)))
                db.commit()
                
                res_txt = (
                    f'<tg-emoji emoji-id="5116175844837950263">📫</tg-emoji> <b>ПОЧТА СОЗДАНА!</b>\n\n'
                    f'<tg-emoji emoji-id="4918408122868958076">📧</tg-emoji> Адрес: <code>{addr}</code>\n'
                    f'<tg-emoji emoji-id="4904714384149840580">🕒</tg-emoji> Истекает через: <b>{h} ч.</b>'
                )
                bot.edit_message_caption(res_txt, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
        except:
            bot.edit_message_caption("❌ Ошибка API Mail.tm. Попробуйте позже.", chat_id=call.message.chat.id, message_id=call.message.message_id)

    elif call.data == "open_inbox":
        bot.answer_callback_query(call.id)
        # Эмуляция нажатия кнопки "Мои письма"
        class M: pass
        m = M(); m.from_user = call.from_user; m.chat = call.message.chat; m.text = "📥 Мои письма"
        text_buttons(m)

# === [ МОНИТОРИНГ ] ===
def check_loop():
    while True:
        try:
            cursor = db.cursor()
            cursor.execute("SELECT user_id, token, expiry FROM active_emails")
            for uid, tk, ex in cursor.fetchall():
                if time.time() > float(ex):
                    cursor.execute("DELETE FROM active_emails WHERE user_id = ?", (uid,))
                    db.commit()
                    continue
                try:
                    r = requests.get(f"{API_URL}/messages", headers={"Authorization": f"Bearer {tk}"}, timeout=5).json()
                    for m in r.get('hydra:member', []):
                        mid = m['id']
                        cursor.execute("SELECT 1 FROM seen_msgs WHERE msg_id = ?", (mid,))
                        if not cursor.fetchone():
                            notif = (
                                f'<tg-emoji emoji-id="4906943755644306322">🔔</tg-emoji> <b>НОВОЕ ПИСЬМО!</b>\n'
                                f'────────────────────\n'
                                f'<tg-emoji emoji-id="4904848288345228262">👤</tg-emoji> От: {m["from"]["address"]}\n'
                                f'<tg-emoji emoji-id="4902524693858222969">📌</tg-emoji> Тема: {m["subject"]}\n'
                                f'────────────────────'
                            )
                            kb = types.InlineKeyboardMarkup()
                            kb.add(types.InlineKeyboardButton("📥 Открыть", callback_data="open_inbox"))
                            bot.send_photo(uid, photo=IMG_LINK, caption=notif, reply_markup=kb, parse_mode='HTML')
                            cursor.execute("INSERT INTO seen_msgs (msg_id) VALUES (?)", (mid,))
                            db.commit()
                except: pass
        except: pass
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=check_loop, daemon=True).start()
    bot.infinity_polling()
