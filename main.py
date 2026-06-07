import os
import sys
import datetime
from pathlib import Path
import telebot
from telebot import types
from dotenv import load_dotenv

from models import Habit, UserSession
from storage import JSONStorage
from services import HabitTrackerService

# Завантажуємо змінні оточення з файлу .env, який лежить поруч із цим файлом.
# Це гарантує надійне зчитування токена навіть при запуску з іншої робочої директорії.
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

# Отримання токена із середовища
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

# Розумна перевірка токена перед ініціалізацією (запобігає помилці util.validate_token)
if not BOT_TOKEN or ":" not in BOT_TOKEN or "вставте_" in BOT_TOKEN:
    print("\n" + "=" * 70)
    print("❌ ПОМИЛКА: НЕВАЛІДНИЙ АБО ВІДСУТНІЙ TELEGRAM BOT TOKEN!")
    print("=" * 70)
    print("Для успішного запуску боту потрібен справжній API-ключ від @BotFather.")
    print("\n👉 ЯК ЦЕ ВИПРАВИТИ:")
    print("1. Переконайтеся, що ви створили файл '.env' у папці проєкту.")
    print("2. Запишіть у нього рядок:")
    print("   BOT_TOKEN=ваш_токен_від_botfather")
    print("=" * 70 + "\n")
    sys.exit(1)

# Ініціалізуємо об'єкти згідно з принципом Dependency Injection (SOLID)
bot = telebot.TeleBot(BOT_TOKEN)
storage = JSONStorage("data/data.json")
service = HabitTrackerService()

# Завантажуємо сесії з бази даних при старті програми
sessions_db = storage.load_all_sessions()


def get_user_session(user_id: int) -> UserSession:
    """Допоміжна функція для отримання або створення сесії користувача."""
    if user_id not in sessions_db:
        session = UserSession(user_id)
        service.init_new_user(session)
        sessions_db[user_id] = session
        storage.save_all_sessions(sessions_db)
    return sessions_db[user_id]


# --- КЛАВІАТУРИ ТА МЕНЮ ---

def main_menu_keyboard() -> types.ReplyKeyboardMarkup:
    """Генерує головне меню бота."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_today = types.KeyboardButton("📝 Звички на сьогодні")
    btn_stats = types.KeyboardButton("📊 Моя статистика")
    btn_manage = types.KeyboardButton("⚙️ Керувати звичками")
    btn_tip = types.KeyboardButton("💫 Отримати підтримку")
    markup.add(btn_today, btn_stats)
    markup.add(btn_manage, btn_tip)
    return markup


# --- ХЕНДЛЕРИ КОМАНД ---

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: types.Message):
    """Обробник вітання при першому запуску бота."""
    user_id = message.chat.id
    get_user_session(user_id)

    welcome_text = (
        f"Вітаю, {message.from_user.first_name}! 🤍\n\n"
        "Я створений для того, щоб підтримати тебе у складні хвилини. "
        "Коли немає сил на великі справи, ми починаємо з крихітних кроків.\n\n"
        "Я підготував для тебе базовий список дій для самопідтримки "
        "(сон, гігієна, вода, прогулянка). Ти можеш змінювати їх або додавати свої.\n\n"
        "Давай піклуватися про себе разом."
    )
    bot.send_message(user_id, welcome_text, reply_markup=main_menu_keyboard())


@bot.message_handler(func=lambda msg: msg.text == "📝 Звички на сьогодні")
def show_today_habits(message: types.Message):
    """Виводить список звичок на сьогодні з можливістю відмітити їх."""
    user_id = message.chat.id
    session = get_user_session(user_id)
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    if not session.habits:
        bot.send_message(user_id, "У тебе наразі немає активних звичок. Додай їх через меню керування!")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    day_logs = session.history.get(today_str, {})

    for habit in session.habits:
        is_done = day_logs.get(habit.habit_id, False)
        status_icon = "✅" if is_done else "⬜"
        button_text = f"{status_icon} {habit.name}"
        callback_data = f"toggle:{habit.habit_id}"
        markup.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))

    rate = session.get_completion_rate(today_str)

    progress_text = (
        f"📋 *Твої звички на сьогодні ({datetime.date.today().strftime('%d.%m')}):*\n"
        f"Натискай на кнопки під цим повідомленням, щоб відзначити виконане.\n\n"
        f"📈 Сьогодні виконано: *{rate:.1f}%*"
    )
    bot.send_message(user_id, progress_text, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle:"))
def handle_habit_toggle(call: types.CallbackQuery):
    """Обробляє натискання на кнопку виконання звички."""
    user_id = call.message.chat.id
    session = get_user_session(user_id)
    habit_id = call.data.split(":")[1]
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    is_completed = session.toggle_habit(today_str, habit_id)
    storage.save_all_sessions(sessions_db)

    rate = session.get_completion_rate(today_str)

    praise_message = ""
    if rate >= 70.0:
        praise_message = "\n\n🎉 *Неймовірно! Ти перейшов за поріг 70%! Твоє тіло та розум вдячні тобі за турботу!*"
    elif is_completed:
        praise_message = f"\n\n✨ Маленька перемога! Крок за кроком тобі стає краще."

    markup = types.InlineKeyboardMarkup(row_width=1)
    day_logs = session.history.get(today_str, {})
    for habit in session.habits:
        status_icon = "✅" if day_logs.get(habit.habit_id, False) else "⬜"
        markup.add(
            types.InlineKeyboardButton(text=f"{status_icon} {habit.name}", callback_data=f"toggle:{habit.habit_id}"))

    new_text = (
        f"📋 *Твої звички на сьогодні ({datetime.date.today().strftime('%d.%m')}):*\n"
        f"Натискай на кнопки під цим повідомленням, щоб відзначити виконане.\n\n"
        f"📈 Сьогодні виконано: *{rate:.1f}%*{praise_message}"
    )

    try:
        bot.edit_message_text(
            chat_id=user_id,
            message_id=call.message.message_id,
            text=new_text,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception:
        pass

    bot.answer_callback_query(call.id, text="Оновлено!")


@bot.message_handler(func=lambda msg: msg.text == "⚙️ Керувати звичками")
def manage_habits_menu(message: types.Message):
    """Виводить меню налаштування звичок (додавання/видалення)."""
    user_id = message.chat.id

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_add = types.KeyboardButton("➕ Додати власну звичку")
    btn_del = types.KeyboardButton("➖ Видалити звичку")
    btn_back = types.KeyboardButton("🔙 Назад до меню")
    markup.add(btn_add, btn_del)
    markup.add(btn_back)

    bot.send_message(
        user_id,
        "Тут ти можеш налаштувати свій список турботи під свої поточні потреби.",
        reply_markup=markup
    )


@bot.message_handler(func=lambda msg: msg.text == "🔙 Назад до меню")
def back_to_main(message: types.Message):
    """Повертає користувача до головного меню."""
    bot.send_message(
        message.chat.id,
        "Повертаємося до головного меню. Пам'ятай, ти все робиш правильно.",
        reply_markup=main_menu_keyboard()
    )


# --- СЦЕНАРІЙ ДОДАВАННЯ ЗВИЧКИ ---

@bot.message_handler(func=lambda msg: msg.text == "➕ Додати власну звичку")
def prompt_add_habit(message: types.Message):
    """Запитує назву нової звички."""
    msg = bot.send_message(
        message.chat.id,
        "Напиши назву звички, яку ти хочеш додати. (Наприклад: 'Прочитати 2 сторінки книги' або 'Погладити кота')"
    )
    bot.register_next_step_handler(msg, process_add_habit_step)


def process_add_habit_step(message: types.Message):
    """Обробляє та валідує введений текст нової звички."""
    user_id = message.chat.id
    habit_name = message.text.strip() if message.text else ""

    if not habit_name or len(habit_name) < 3:
        bot.send_message(user_id, "❌ Назва звички занадто коротка. Спробуй ще раз.")
        return

    session = get_user_session(user_id)
    habit_id = f"custom_{int(datetime.datetime.now().timestamp())}"
    new_habit = Habit(habit_id=habit_id, name=habit_name, is_default=False)

    try:
        session.add_habit(new_habit)
        storage.save_all_sessions(sessions_db)
        bot.send_message(user_id, f"✅ Звичку успішно додано: \"{habit_name}\"!", reply_markup=main_menu_keyboard())
    except Exception:
        bot.send_message(user_id, "❌ Сталася помилка при збереженні звички. Спробуйте пізніше.")


# --- СЦЕНАРІЙ ВИДАЛЕННЯ ЗВИЧКИ ---

@bot.message_handler(func=lambda msg: msg.text == "➖ Видалити звичку")
def show_delete_menu(message: types.Message):
    """Виводить список для видалення через inline-кнопки."""
    user_id = message.chat.id
    session = get_user_session(user_id)

    if not session.habits:
        bot.send_message(user_id, "Твій список звичок порожній.")
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for habit in session.habits:
        markup.add(types.InlineKeyboardButton(text=f"🗑️ {habit.name}", callback_data=f"delete:{habit.habit_id}"))

    bot.send_message(user_id, "Вибери звичку, яку ти хочеш видалити зі списку активних:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete:"))
def handle_delete_callback(call: types.CallbackQuery):
    """Видаляє звичку за вибором користувача."""
    user_id = call.message.chat.id
    session = get_user_session(user_id)
    habit_id = call.data.split(":")[1]

    if session.remove_habit(habit_id):
        storage.save_all_sessions(sessions_db)
        bot.answer_callback_query(call.id, text="Звичку видалено!")
        if session.habits:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for habit in session.habits:
                markup.add(
                    types.InlineKeyboardButton(text=f"🗑️ {habit.name}", callback_data=f"delete:{habit.habit_id}"))
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="Вибери звичку для видалення:",
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=user_id,
                message_id=call.message.message_id,
                text="Усі звички видалено."
            )
    else:
        bot.answer_callback_query(call.id, text="Помилка при видаленні.")


# --- СТАТИСТИКА ТА ПОРАДИ ---

@bot.message_handler(func=lambda msg: msg.text == "📊 Моя статистика")
def show_statistics(message: types.Message):
    """Формує звіт за допомогою pandas та надсилає згенероване зображення графіка."""
    user_id = message.chat.id
    session = get_user_session(user_id)

    msg_wait = bot.send_message(user_id, "Збираю дані твого прогресу та малюю графік... 🎨")

    try:
        image_path = service.generate_weekly_report(session)

        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as photo:
                bot.send_photo(
                    user_id,
                    photo,
                    caption="Ось твоя тижнева статистика. Кожен заповнений стовпчик — це твоя перемога над апатією. Продовжуй турбуватися про себе!"
                )
            os.remove(image_path)
        else:
            bot.send_message(user_id, "Не вдалося згенерувати графік. Спробуй відзначити кілька звичок спочатку.")
    except Exception as e:
        bot.send_message(user_id, "Сталася помилка при побудові графіка. Спробуй пізніше.")
    finally:
        try:
            bot.delete_message(user_id, msg_wait.message_id)
        except Exception:
            pass


@bot.message_handler(func=lambda msg: msg.text == "💫 Отримати підтримку")
def send_mental_advice(message: types.Message):
    """Надсилає теплу надихаючу цитату підтримки."""
    tip = service.get_random_tip()
    bot.send_message(message.chat.id, f"💫 *Хвилинка тепла для тебе:*\n\n{tip}", parse_mode="Markdown")


# --- СТАРТ БОТА ---

if __name__ == "__main__":
    print("[INFO] Бот запущений та готовий до роботи...")
    try:
        bot.infinity_polling(skip_pending=True)
    except KeyboardInterrupt:
        print("[INFO] Роботу бота припинено користувачем.")