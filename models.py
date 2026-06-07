import datetime
from typing import List, Dict, Any

class Habit:
    """Клас, що представляє окрему звичку користувача."""
    
    def __init__(self, habit_id: str, name: str, is_default: bool = False):
        self.habit_id: str = habit_id
        self.name: str = name
        self.is_default: bool = is_default

    def to_dict(self) -> Dict[str, Any]:
        """Конвертує об'єкт класу в словник для збереження в JSON."""
        return {
            "habit_id": self.habit_id,
            "name": self.name,
            "is_default": self.is_default
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Habit":
        """Створює об'єкт класу зі словника JSON."""
        return cls(
            habit_id=data["habit_id"],
            name=data["name"],
            is_default=data.get("is_default", False)
        )

    def __str__(self) -> str:
        """Рядкове представлення звички (вимога до тадіс-методу)."""
        prefix = "⭐️ [Базова]" if self.is_default else "📌 [Власна]"
        return f"{prefix} {self.name}"


class UserSession:
    """Клас для керування сесією користувача, його списком звичок та прогресом."""
    
    def __init__(self, user_id: int):
        self.user_id: int = user_id
        self.habits: List[Habit] = []
        # Структура історії: { "YYYY-MM-DD": { "habit_id": True/False } }
        self.history: Dict[str, Dict[str, bool]] = {}

    def add_habit(self, habit: Habit) -> None:
        """Додає нову звичку в профіль користувача, якщо такої ще немає."""
        if not any(h.habit_id == habit.habit_id for h in self.habits):
            self.habits.append(habit)

    def remove_habit(self, habit_id: str) -> bool:
        """Видаляє звичку за її ID та очищує її з поточної історії."""
        initial_len = len(self.habits)
        self.habits = [h for h in self.habits if h.habit_id != habit_id]
        
        # Видаляємо згадки з історії, щоб не накопичувати неіснуючі ID
        for date_str in self.history:
            if habit_id in self.history[date_str]:
                del self.history[date_str][habit_id]
                
        return len(self.habits) < initial_len

    def toggle_habit(self, date_str: str, habit_id: str) -> bool:
        """Перемикає статус виконання звички (виконано/не виконано) на певну дату."""
        if date_str not in self.history:
            self.history[date_str] = {}
        
        current_status = self.history[date_str].get(habit_id, False)
        self.history[date_str][habit_id] = not current_status
        return self.history[date_str][habit_id]

    def get_completion_rate(self, date_str: str) -> float:
        """
        Обчислює відсоток виконаних звичок за конкретний день.
        Формула: P = (Виконано / Всього активних) * 100
        """
        if not self.habits:
            return 0.0
        
        day_logs = self.history.get(date_str, {})
        completed_count = sum(1 for h in self.habits if day_logs.get(h.habit_id, False))
        return (completed_count / len(self.habits)) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Конвертує сесію користувача у словник для JSON."""
        return {
            "user_id": self.user_id,
            "habits": [h.to_dict() for h in self.habits],
            "history": self.history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSession":
        """Створює об'єкт сесії користувача з розпарсеного JSON."""
        session = cls(user_id=data["user_id"])
        session.habits = [Habit.from_dict(h) for h in data.get("habits", [])]
        session.history = data.get("history", {})
        return session

    def __str__(self) -> str:
        return f"Користувач ID: {self.user_id} | Активних звичок: {len(self.habits)}"