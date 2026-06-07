import datetime
import random
from typing import List, Dict, Optional
import pandas as pd
import matplotlib
# Використовуємо неінтерактивний бекенд для запобігання помилок у середовищах без GUI
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os

from models import UserSession, Habit

class HabitTrackerService:
    """Клас сервісу бізнес-логіки та аналітики даних."""

    def __init__(self):
        # Дефолтний терапевтичний список звичок для людей з депресивним/тривожним спектром
        self.default_habits_pool: List[Dict[str, Any]] = [
            {"id": "sleep", "name": "💤 Поспати 7-8 годин"},
            {"id": "teeth", "name": "🪥 Почистити зуби та вмитися"},
            {"id": "shower", "name": "🚿 Прийняти теплий душ (турбота про тіло)"},
            {"id": "bed", "name": "🛏️ Застелити ліжко (перша маленька перемога)"},
            {"id": "meds", "name": "💊 Прийняти ліки або вітаміни за розкладом"},
            {"id": "water", "name": "💧 Випити склянку чистої води"},
            {"id": "meal", "name": "🍲 Збалансовано поїсти (хоча б трохи)"},
            {"id": "outdoor", "name": "🌳 Вийти на свіже повітря (хоча б на 5-10 хв)"},
            {"id": "stretch", "name": "🧘 Легка розминка або потягування тіла"}
        ]

        # Список мотиваційних фраз та порад для підтримки ментального здоров'я
        self._mental_tips: List[str] = [
            "Пам'ятай: навіть найменший крок — це вже рух уперед. Ти велика сила, що бореться.",
            "Якщо сьогодні твій максимум — просто вмити обличчя, це вже перемога. Пишайся собою.",
            "Твоя цінність не вимірюється продуктивністю. Дозволь собі рухатись у власному темпі.",
            "Твоє тіло — твій дім. Обійми себе думками. Ти робиш усе, що в твоїх силах.",
            "Складні дні минають. Головне — бути лагідним до себе прямо зараз.",
            "Зроби глибокий вдих. Затримай дихання на 4 секунди. Повільно видихни. Ти в безпеці.",
            "Тобі не потрібно згортати гори щодня. Достатньо просто піклуватися про себе по краплинці."
        ]

    def init_new_user(self, session: UserSession) -> None:
        """Наповнює новий профіль користувача дефолтними звичками."""
        for item in self.default_habits_pool:
            habit = Habit(habit_id=item["id"], name=item["name"], is_default=True)
            session.add_habit(habit)

    def get_random_tip(self) -> str:
        """Повертає випадкову пораду підтримки."""
        return random.choice(self._mental_tips)

    def generate_weekly_report(self, session: UserSession) -> Optional[str]:
        """
        Аналізує дані за останні 7 днів за допомогою pandas та
        генерує графік за допомогою matplotlib. Повертає шлях до файлу зображення.
        """
        if not session.habits:
            return None

        # Визначаємо список останніх 7 дат
        today = datetime.date.today()
        dates = [today - datetime.timedelta(days=i) for i in range(6, -1, -1)]
        dates_str = [d.strftime("%Y-%m-%d") for d in dates]
        readable_dates = [d.strftime("%d.%m") for d in dates]

        # Збираємо дані для аналізу через pandas DataFrame
        data_records = []
        for d_str, r_d in zip(dates_str, readable_dates):
            rate = session.get_completion_rate(d_str)
            data_records.append({"Дата": r_d, "Прогрес (%)": rate})

        df = pd.DataFrame(data_records)

        # Створюємо графік
        plt.figure(figsize=(8, 4.5))
        
        # Стилізація для підтримки спокійного тону (м'які пастельні відтінки)
        colors = ['#7BB779' if val >= 70.0 else '#D4F1D3' for val in df["Прогрес (%)"]]
        
        bars = plt.bar(df["Дата"], df["Прогрес (%)"], color=colors, edgecolor='#7BB779', width=0.6, zorder=3)
        
        # Лінія цілі у 70% для мотивації
        plt.axhline(y=70, color='#BE5D87', linestyle='--', linewidth=1.5, label='Ціль самотурботи (70%)', zorder=4)

        # Налаштування осей та сітки
        plt.title("Твій тижневий прогрес самотурботи", fontsize=14, pad=15, color='#264653', fontweight='bold')
        plt.xlabel("Дата", fontsize=11, labelpad=10, color='#264653')
        plt.ylabel("Виконано звичок (%)", fontsize=11, labelpad=10, color='#264653')
        plt.ylim(0, 105)
        plt.grid(axis='y', linestyle=':', alpha=0.6, zorder=0)
        plt.legend(loc='upper left', frameon=True, facecolor='#f8f9fa')

        # Додавання значень над стовпчиками
        for bar in bars:
            height = bar.get_height()
            plt.annotate(f'{height:.0f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=9, color='#1d3557', fontweight='semibold')

        # Додаткове візуальне покращення дизайну рамки
        for spine in plt.gca().spines.values():
            spine.set_color('#cccccc')

        plt.tight_layout()

        # Зберігаємо графік у тимчасовий файл
        os.makedirs("temp", exist_ok=True)
        filepath = f"temp/stats_{session.user_id}.png"
        plt.savefig(filepath, dpi=150)
        plt.close()
        
        return filepath