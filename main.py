ME_ID = 1127025574
import telebot, methods, logging, asyncio
import telebot.async_telebot
import os
from dotenv import load_dotenv

load_dotenv()

prdxs = ["prdx", "парадокс"]
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%d/%m/%Y %I:%M:%S %p",
    handlers=[
        logging.FileHandler("./logs.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

bot = telebot.async_telebot.AsyncTeleBot(os.getenv("TOKEN"))


@bot.message_handler(commands=["start"])
async def start(message):
    z = ", ".join(prdxs)
    await bot.send_message(message.chat.id, f"Доступные команды: \n{z}, карты, баланс")


@bot.message_handler(commands=["anoncment"])
async def anoncment(message):
    if message.from_user.id != ME_ID:
        if message.from_user.id == 1472118418 or message.from_user.id == 7767572246:
            await bot.send_message(message.from_user.id, "Мурчиков iдi нахуй")
            return
        else:
            await bot.send_message(message.from_user.id, "Ты кто?")
            return

    users = methods.get_users_id()
    text = message.text.replace("/anoncment", "").strip()
    if not text:
        await bot.send_message(message.from_user.id, "Введите текст для рассылки")
    for user in users:
        try:
            await bot.send_message(user, text)
        except Exception as e:
            logging.error(f"Error anoncment {e}")
            await bot.send_message(
                message.from_user.id, f"Ошибка при отправке сообщения {e} \nЮзер {user}"
            )


@bot.message_handler(commands=["prdx"])
async def prdx(message):
    await methods.generate_prdx(message, bot)


@bot.message_handler(commands=["cards"])
async def cards(message):
    markup = await methods.generate_markup_cards(message)
    await bot.send_message(message.chat.id, f"✨ Выберите карточку:", reply_markup=markup)


@bot.message_handler(commands=["balance"])
async def balance(message):
    money = await methods.get_user_money(message.from_user.id)
    money = money[0]
    await bot.send_message(
        message.chat.id,
        f"Ваши монеты: {money}",
    )


@bot.message_handler(content_types=["text"])
async def text(message):
    if message.text.lower() in prdxs:
        await methods.generate_prdx(message, bot)

    if message.text.lower() == "карты":
        markup = await methods.generate_markup_cards(message)
        await bot.send_message(message.chat.id, f"✨ Выберите карточку:", reply_markup=markup)

    if message.text.lower() == "баланс":
        money = await methods.get_user_money(message.from_user.id)
        money = money[0]
        await bot.send_message(
            message.chat.id,
            f"Ваши монеты: {money}",
        )


@bot.callback_query_handler(func=lambda callback: True)
async def callback_message(callback):
    if callback.data.startswith("card_"):
        data = callback.data.split("_")
        card_id = int(data[1])
        user_id = int(data[2])

        # Проверяем пользователя
        if callback.from_user.id != user_id:
            await bot.answer_callback_query(callback.id, text="Это не ваша кнопка")
            return

        card = await methods.get_card_by_id(card_id)
        markup = telebot.types.InlineKeyboardMarkup()

        name = card.get("name")
        rare = card.get("rare")
        money = card.get("money")
        img = card.get("img")

        markup.add(
            telebot.types.InlineKeyboardButton(
                text="Назад",
                callback_data=f"back",  # callback_data нужен для обработки нажатия
            )
        )

        await bot.edit_message_media(
            chat_id=callback.message.chat.id,
            media=telebot.types.InputMediaPhoto(
                media=open(img, "rb"),
                caption=f"{name}\n💎 Редкость • {rare}\n💰 Стоимость • {money} монет",
            ),
            message_id=callback.message.message_id,
            reply_markup=markup,
        )
    if callback.data == "back":
        markup = await methods.generate_markup_cards(callback)
        await bot.delete_message(
            chat_id=callback.message.chat.id, message_id=callback.message.message_id
        )
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text="Выберите карточку:",
            reply_markup=markup,
        )
async def run():
    name = await bot.get_my_name()
    name = name.name
    logging.info(f"loggined as {name}")
    await bot.polling()


asyncio.run(run())

logging.info("Bot stopped")
