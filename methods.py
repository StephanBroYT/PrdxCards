import sqlite3
import json
import telebot
import random
import logging
import datetime

def setup_database():
    conn = sqlite3.connect("komaru.db")
    c = conn.cursor()

    c.execute(
        """CREATE TABLE IF NOT EXISTS users
            (user_id INTEGER PRIMARY KEY,
            money INTEGER)"""
    )

    c.execute(
        """CREATE TABLE IF NOT EXISTS user_cards
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            UNIQUE(user_id, card_id))"""
    )

    c.execute("""
        CREATE TABLE IF NOT EXISTS cooldowns (
            user_id INTEGER PRIMARY KEY,
            last_use TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


setup_database()

def check_cooldown(user_id: int) -> tuple[bool, str]:
    conn = sqlite3.connect("komaru.db")
    c = conn.cursor()
    
    c.execute("SELECT last_use FROM cooldowns WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    
    if result:
        last_use = datetime.datetime.fromisoformat(result[0])
        now = datetime.datetime.now()
        diff = now - last_use
        
        if diff < datetime.timedelta(seconds=5):
            remaining = datetime.timedelta(seconds=5) - diff
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            seconds = remaining.seconds % 60
            
            time_str = ""
            if hours > 0:
                time_str += f"{hours}ч. "
            if minutes > 0:
                time_str += f"{minutes}мин. "
            time_str += f"{seconds}сек"
            
            return False, time_str
            
    c.execute("INSERT OR REPLACE INTO cooldowns (user_id, last_use) VALUES (?, ?)",
              (user_id, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return True, ""

def add_card_to_user(user_id: int, card_id: int) -> bool:
    """Добавляет карточку пользователю"""
    try:
        conn = sqlite3.connect("komaru.db")
        c = conn.cursor()

        money = get_card_by_id(card_id).get("money", 0)
        c.execute(
            "INSERT OR IGNORE INTO users (user_id, money) VALUES (?, ?)",
            (user_id, money),
        )

        c.execute(
            "INSERT OR IGNORE INTO user_cards (user_id, card_id) VALUES (?, ?)",
            (user_id, card_id),
        )

        c.execute(
            "UPDATE users SET money = money + ? WHERE user_id = ?", (money, user_id)
        )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logging.error(f"Error adding card: {e}")
        return False


def get_user_cards(user_id: int) -> list:
    """Возвращает список ID карточек пользователя"""
    try:
        with sqlite3.connect("komaru.db") as conn:
            c = conn.cursor()
            c.execute("SELECT card_id FROM user_cards WHERE user_id = ?", (user_id,))
            return [card[0] for card in c.fetchall()]
    except Exception as e:
        logging.error(f"Ошибка при получении карточек: {e}")
        return []


def get_user_money(user_id: int) -> list:
    """Возвращает список ID карточек пользователя"""
    try:
        with sqlite3.connect("komaru.db") as conn:
            c = conn.cursor()
            c.execute("SELECT money FROM users WHERE user_id = ?", (user_id,))
            return [card[0] for card in c.fetchall()]
    except Exception as e:
        logging.error(f"Ошибка при получении монет: {e}")
        return []


def get_users_id() -> list:
    """Возвращает список ID пользователей"""
    try:
        with sqlite3.connect("komaru.db") as conn:
            c = conn.cursor()
            c.execute("SELECT user_id FROM users")
            return [card[0] for card in c.fetchall()]
    except Exception as e:
        logging.error(f"Ошибка при получении ids: {e}")
        return []


def get_cards() -> list:
    """Возвращает список всех карточек"""
    try:
        with open("komars.json", "r", encoding="UTF-8") as file:
            cards = json.loads(file.read())
            return cards
    except Exception as e:
        logging.error(f"Ошибка при получении карточек: {e}")
        return {}


def get_card_by_id(card_id: str) -> dict:
    """Возвращает информацию о карточке по её ID из JSON файла"""
    try:
        with open("komars.json", "r", encoding="UTF-8") as file:
            cards = json.loads(file.read())
            return cards.get(str(card_id), {})
    except Exception as e:
        logging.error(f"Ошибка при получении карточки: {e}")
        return {}


def generate_markup_cards(message):
    markup = telebot.types.InlineKeyboardMarkup()

    for i in get_user_cards(message.from_user.id):
        card = get_card_by_id(i)
        markup.add(
            telebot.types.InlineKeyboardButton(
                text=f"{card.get('name')} {card.get('rare')}",
                callback_data=f"card_{i}_{message.from_user.id}",
            )
        )
    return markup


def generate_komar(message, bot):
    try:
        can_use, time_left = check_cooldown(message.from_user.id)
        if not can_use:
            bot.reply_to(message, f"🕖 Вы не смогли найти КОМАРА, попробуйте через {time_left}")
            return

        komar_id = random.choice(list(get_cards()))
        komar_data = get_card_by_id(komar_id)

        name = komar_data.get("name")
        rare = komar_data.get("rare")
        money = komar_data.get("money")
        img = komar_data.get("img")

        # logging.info(f"id:{komar_id} data:{komar_data}")
        cards = get_user_cards(message.from_user.id)
        # logging.info(komar_id, cards)
        dupe = int(komar_id) in cards
        
        add_card_to_user(message.from_user.id, komar_id)

        if dupe:
            bot.send_photo(
            chat_id=message.chat.id,
            photo=open(img, "rb"),
            caption=f"🚀 Вам *повторно* выпала карточка {name} \n💎 Редкость • {rare} \n💰 Вам добавлено {money} монет \n||ID: {komar_id}||",
            parse_mode="MarkdownV2",
        )
        else:
            bot.send_photo(
            chat_id=message.chat.id,
            photo=open(img, "rb"),
            caption=f"🚀 Вам выпала карточка {name} \n💎 Редкость • {rare} \n💰 Вам добавлено {money} монет \n||ID: {komar_id}||",
            parse_mode="MarkdownV2",
        )



    except Exception as e:
        logging.error(f"Error {e}")
