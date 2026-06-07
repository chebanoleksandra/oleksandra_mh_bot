import os
import sys
import pytest

# Додаємо батьківську директорію до системного шляху, щоб уникнути помилок імпорту
# незалежно від того, з якої папки запускаються тести.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import Habit, UserSession
from storage import JSONStorage


@pytest.fixture
def test_habit() -> Habit:
    """Фікстура для створення тестової звички."""
    return Habit(habit_id="test_1", name="Тестова звичка", is_default=False)


@pytest.fixture
def session() -> UserSession:
    """Фікстура для створення сесії користувача."""
    return UserSession(user_id=9999)


@pytest.fixture
def temp_storage(tmp_path) -> tuple[JSONStorage, str]:
    """
    Фікстура для ізольованого тестування файлового сховища.
    Використовує вбудовану в pytest фікстуру tmp_path для створення тимчасової папки.
    """
    test_file = tmp_path / "test_db.json"
    storage = JSONStorage(str(test_file))
    return storage, str(test_file)


def test_habit_creation_and_str(test_habit: Habit) -> None:
    """Тест 1: Перевірка правильного створення об'єкту та методу __str__."""
    assert test_habit.habit_id == "test_1"
    assert test_habit.name == "Тестова звичка"
    assert test_habit.is_default is False
    assert "Тестова звичка" in str(test_habit)


def test_add_and_remove_habit(session: UserSession, test_habit: Habit) -> None:
    """Тест 2: Перевірка додавання та видалення звички із сесії."""
    # Додавання нової звички
    session.add_habit(test_habit)
    assert len(session.habits) == 1
    assert session.habits[0].habit_id == "test_1"

    # Спроба додати дублікат не повинна змінювати довжину списку
    session.add_habit(test_habit)
    assert len(session.habits) == 1

    # Видалення звички
    removed = session.remove_habit("test_1")
    assert removed is True
    assert len(session.habits) == 0


def test_completion_calculations(session: UserSession) -> None:
    """Тест 3: Перевірка математичної логіки обчислення відсотка виконання звичок."""
    h1 = Habit(habit_id="h1", name="Звичка 1")
    h2 = Habit(habit_id="h2", name="Звичка 2")
    
    session.add_habit(h1)
    session.add_habit(h2)

    date_key = "2026-06-07"
    
    # Спочатку виконано 0%
    assert session.get_completion_rate(date_key) == 0.0

    # Виконуємо першу звичку -> 50%
    session.toggle_habit(date_key, "h1")
    assert session.get_completion_rate(date_key) == 50.0

    # Виконуємо другу звичку -> 100%
    session.toggle_habit(date_key, "h2")
    assert session.get_completion_rate(date_key) == 100.0

    # Скасовуємо виконання першої звички -> знову 50%
    session.toggle_habit(date_key, "h1")
    assert session.get_completion_rate(date_key) == 50.0


def test_storage_save_and_load(temp_storage: tuple[JSONStorage, str]) -> None:
    """Тест 4: Перевірка збереження даних у файл та коректного зчитування."""
    storage, test_file_path = temp_storage
    
    session = UserSession(user_id=123)
    session.add_habit(Habit("h1", "Тест"))
    session.toggle_habit("2026-06-07", "h1")

    db = {123: session}
    save_success = storage.save_all_sessions(db)
    
    # Перевіряємо успішність запису та фізичну наявність файлу
    assert save_success is True
    assert os.path.exists(test_file_path)

    # Завантажуємо базу назад та перевіряємо цілісність даних
    loaded_db = storage.load_all_sessions()
    assert 123 in loaded_db
    assert len(loaded_db[123].habits) == 1
    assert loaded_db[123].habits[0].name == "Тест"
    assert loaded_db[123].history["2026-06-07"]["h1"] is True