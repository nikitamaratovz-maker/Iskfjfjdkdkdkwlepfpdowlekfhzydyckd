import telebot
import sqlite3
import requests
import time
import threading
import re
import random
import string
from telebot import types

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = "8710963699:AAFZ8j_ASTp_wMtxgHV2vf_TXazExyTyR60"
BOT_USERNAME = "KrestblMailBot" 
ADMIN_ID = 8727723180
REQUIRED_CHANNEL = "@krectbll"
CHANNEL_LINK = "https://t.me/krectbll"
API_URL = "https://api.mail.tm"
IMG_LINK = "https://i.postimg.cc/50j8fp2c/Picsart-26-04-20-22-01-28-165.jpg"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='HTML')

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect('krestbl_logic_v4.db', check_same_thread=False)
    cursor = conn.cursor()
    # Добавлена колонка is_counted, чтобы не давать бонус дважды
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                   (user_id INTEGER PRIMARY KEY, mails_left INTEGER DEFAULT 1, 
                    ref_count INTEGER DEFAULT 0, referrer_id INTEGER, is_counted INTEGER DEFAULT 0)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_emails 
                   (user_id INTEGER PRIMARY KEY, email TEXT, token TEXT, expiry TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS seen_msgs (msg_id TEXT PRIMARY KEY)''')
    conn.commit()
    return conn

db = init_db()

# === СИСТЕМНЫЕ ФУНКЦИИ ===
def is_sub(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

def get_user(user_id):
    cursor = db.cursor()
    cursor.execute("SELECT mails_left, ref_count, referrer_id, is_counted FROM users WHERE user_id = ?", (user_id,))
    return cursor.fetchone()

def send_layout(chat_id, text, markup=None):
    return bot.send_photo(chat_id, photo=IMG_LINK, caption=text, reply_markup=markup, parse_mode='HTML')

# === ОБРАБОТЧИКИ ===

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    cursor = db.cursor()
    
    user = get_user(user_id)
    
    # Если юзера нет в базе, создаем запись
    if not user:
        ref_id = None
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            ref_id = int(args[1])
            if ref_id == user_id: ref_id = None
        
        cursor.execute("INSERT INTO users (user_id, referrer_id, is_counted) VALUES (?, ?, 0)", (user_id, ref_id))
        db.commit()
        user = get_user(user_id)

    # ПРОВЕРКА ПОДПИСКИ
    if not is_sub(user_id):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("➡️ Подписаться на канал", url=CHANNEL_LINK))
        kb.add(types.InlineKeyboardButton("🔄 Проверить подписку", callback_data="check_sub"))
        send_layout(message.chat.id, "<b>📍 KRESTBL MAIL GENERATOR</b>\n\nБонус за регистрацию и доступ к боту выдаются только <b>после подписки</b> на наш канал.", markup=kb)
        return

    # ЕСЛИ ПОДПИСАН И БОНУС ЕЩЕ НЕ ВЫДАН ПРИГЛАСИВШЕМУ
    if user[3] == 0: # is_counted == 0
        if user[2]: # если есть referrer_id
            ref_id = user[2]
            cursor.execute("UPDATE users SET mails_left = mails_left + 1, ref_count = ref_count + 1 WHERE user_id = ?", (ref_id,))
            cursor.execute("UPDATE users SET is_counted = 1 WHERE user_id = ?", (user_id,))
            db.commit()
            try:
                send_layout(ref_id, f"<b>🎁 Реферал засчитан!</b>\n\nВаш приглашенный друг подписался на канал. Вам начислено <b>+1 создание почты</b>.")
            except: pass
        else:
            # Если пришел сам, просто помечаем как проверенного
            cursor.execute("UPDATE users SET is_counted = 1 WHERE user_id = ?", (user_id,))
            db.commit()

    send_layout(message.chat.id, "<b>📍 KRESTBL MAIL GENERATOR</b>\n\nВы успешно авторизованы. Используйте меню для работы.", markup=main_kb())

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_callback(call):
    if is_sub(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start(call.message) # Перезапускаем старт для начисления бонуса
    else:
        bot.answer_callback_query(call.id, "❌ Вы всё еще не подписаны!", show_alert=True)

# === ОСТАЛЬНЫЕ ФУНКЦИИ (БЕЗ ИЗМЕНЕНИЙ) ===

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

@bot.message_handler(func=lambda m: m.text == "⚡️ Создать почту")
def create_mail_btn(message):
    u = get_user(message.from_user.id)
    if u[0] <= 0:
        send_layout(message.chat.id, "<b>❌ Нет попыток</b>\n\nПригласите друзей в разделе «Партнерка», чтобы получить новые создания.")
        return
    send_layout(message.chat.id, "<b>⏳ Время жизни</b>\n\nВыберите срок действия почты:", markup=time_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("settime_"))
def finalize_mail(call):
    hours = int(call.data.split("_")[1])
    bot.edit_message_caption("<b>🛰 Создаю адрес...</b>", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
    try:
        domains = requests.get(f"{API_URL}/domains").json()['hydra:member']
        domain = domains[0]['domain']
        login = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"krest_{login}@{domain}"
        password = "pwd" + login
        reg = requests.post(f"{API_URL}/accounts", json={"address": address, "password": password})
        if reg.status_code == 201:
            token = requests.post(f"{API_URL}/token", json={"address": address, "password": password}).json()['token']
            expiry = time.time() + (hours * 3600)
            cursor = db.cursor()
            cursor.execute("UPDATE users SET mails_left = mails_left - 1 WHERE user_id = ?", (call.from_user.id,))
            cursor.execute("REPLACE INTO active_emails VALUES (?, ?, ?, ?)", (call.from_user.id, address, token, expiry))
            db.commit()
            res = (f"<b>✅ Готово</b>\n────────────────────\n📫 Адрес: <code>{address}</code>\n🕒 Активна: <b>{hours} ч.</b>\n────────────────────")
            bot.edit_message_caption(res, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')
    except: bot.edit_message_caption("❌ Ошибка API.", chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode='HTML')

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile_btn(message):
    u = get_user(message.from_user.id)
    send_layout(message.chat.id, f"<b>👤 Профиль</b>\n────────────────────\n🆔 ID: <code>{message.from_user.id}</code>\n✉️ Осталось создание почт: <b>{u[0]}</b>\n👥 Друзей: <b>{u[1]}</b>\n────────────────────")

@bot.message_handler(func=lambda m: m.text == "🔗 Партнерка")
def ref_btn(message):
    link = f"https://t.me/{BOT_USERNAME}?start={message.from_user.id}"
    send_layout(message.chat.id, f"<b>🤝 Партнерка</b>\n────────────────────\n🎁 Бонус: <b>+1 создание почты</b> за каждого подписавшегося друга.\n🔗 Ссылка: <code>{link}</code>")

@bot.message_handler(func=lambda m: m.text == "📥 Мои письма")
def check_manual(message):
    cursor = db.cursor()
    cursor.execute("SELECT email FROM active_emails WHERE user_id = ?", (message.from_user.id,))
    email = cursor.fetchone()
    if not email: send_layout(message.chat.id, "<b>📭 Нет активной почты.</b>")
    else: send_layout(message.chat.id, f"<b>🔎 Почта:</b> <code>{email[0]}</code>\nОжидайте писем.")

# === АДМИН ПАНЕЛЬ ===
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📢 Рассылка", "💎 Выдать попытки", "🔙 Главное меню")
    send_layout(message.chat.id, "<b>👑 Админ-панель</b>", markup=kb)

@bot.message_handler(func=lambda m: m.text == "💎 Выдать попытки" and m.from_user.id == ADMIN_ID)
def admin_give(message):
    msg = bot.send_message(message.chat.id, "Введите: <code>ID КОЛИЧЕСТВО</code>")
    bot.register_next_step_handler(msg, admin_give_done)

def admin_give_done(message):
    try:
        uid, count = map(int, message.text.split())
        cursor = db.cursor()
        cursor.execute("UPDATE users SET mails_left = mails_left + ? WHERE user_id = ?", (count, uid))
        db.commit()
        bot.send_message(message.chat.id, "✅ Успешно.")
    except: bot.send_message(message.chat.id, "❌ Ошибка.")

@bot.message_handler(func=lambda m: m.text == "🔙 Главное меню")
def back_main(message):
    bot.send_message(message.chat.id, "Меню открыто.", reply_markup=main_kb())

# === ЦИКЛ МОНИТОРИНГА ===
def check_loop():
    while True:
        try:
            cursor = db.cursor()
            cursor.execute("SELECT user_id, token, expiry FROM active_emails")
            for uid, token, exp in cursor.fetchall():
                if time.time() > float(exp):
                    cursor.execute("DELETE FROM active_emails WHERE user_id = ?", (uid,))
                    db.commit()
                    send_layout(uid, "<b>⌛️ Срок жизни ящика истек.</b>")
                    continue
                res = requests.get(f"{API_URL}/messages", headers={"Authorization": f"Bearer {token}"}).json()
                for m in res.get('hydra:member', []):
                    m_id = m['id']
                    cursor.execute("SELECT 1 FROM seen_msgs WHERE msg_id = ?", (m_id,))
                    if not cursor.fetchone():
                        full = requests.get(f"{API_URL}/messages/{m_id}", headers={"Authorization": f"Bearer {token}"}).json()
                        # Теперь мы не достаем body и code здесь, а просто уведомляем
                        out = (
                            f"<b>📩 Получено новое письмо!</b>\n"
                            f"────────────────────\n"
                            f"👤 От: {m['from']['address']}\n"
                            f"📌 Тема: {m['subject']}\n"
                            f"────────────────────\n"
                            f"<i>Нажмите на кнопку ниже, чтобы перейти к просмотру.</i>"
                        )
                        
                        # Создаем кнопку быстрого перехода
                        kb = types.InlineKeyboardMarkup()
                        kb.add(types.InlineKeyboardButton("📥 Открыть входящие", callback_data="open_inbox"))
                        
                        # Отправляем компактное уведомление с фото
                        send_layout(uid, out, markup=kb)
                        
                        # РЕГИСТРИРУЕМ ПИСЬМО В БАЗЕ (Обязательно!)
                        cursor.execute("INSERT INTO seen_msgs VALUES (?)", (m_id,))
                        db.commit()

        except: pass
        time.sleep(10)

if __name__ == "__main__":
    threading.Thread(target=check_loop, daemon=True).start()
    bot.infinity_polling()
