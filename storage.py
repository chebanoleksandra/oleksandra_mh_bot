import json
import os
from typing import Dict, Any
from models import UserSession

class JSONStorage:
    """Клас для роботи з файловою системою (збереження прогресу користувачів)."""
    
    def __init__(self, filepath: str = "data/data.json"):
        self.filepath: str = filepath
        # Гарантуємо створення папки для збереження файлу
        directory = os.path.dirname(self.filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

    def load_all_sessions(self) -> Dict[int, UserSession]:
        """Завантажує всі сесії користувачів із файлу JSON."""
        if not os.path.exists(self.filepath):
            return {}
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                sessions: Dict[int, UserSession] = {}
                for user_id_str, user_data in raw_data.items():
                    user_id = int(user_id_str)
                    sessions[user_id] = UserSession.from_dict(user_data)
                return sessions
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Помилка при зчитуванні файлу даних: {e}. Створюємо чисту базу.")
            return {}
        except Exception as e:
            print(f"Непередбачувана помилка файлової системи: {e}")
            return {}

    def save_all_sessions(self, sessions: Dict[int, UserSession]) -> bool:
        """Зберігає всі сесії користувачів у файл JSON."""
        try:
            data_to_save = {str(uid): sess.to_dict() for uid, sess in sessions.items()}
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            print(f"Помилка введення-виведення при записі у файл: {e}")
            return False
        except Exception as e:
            print(f"Не вдалося зберегти дані: {e}")
            return False