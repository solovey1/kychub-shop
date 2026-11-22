import random
from collections.abc import Collection
from itertools import count
from typing import Final

# What an executor is called when the admin did not pick a name: cartoon characters.
DEFAULT_ALIASES: Final = (
    "Губка Боб", "Патрик", "Сквидвард", "Мистер Крабс", "Сэнди", "Планктон", "Гэри", "Перл",
    "Миссис Пафф", "Ларри", "Барт", "Гомер", "Мардж", "Лиза", "Апу", "Нед", "Рик", "Морти",
    "Финн", "Джейк", "Бимо", "Марселин", "Крош", "Ёжик", "Нюша", "Бараш", "Лосяш", "Копатыч",
    "Совунья", "Кар-Карыч", "Пин", "Биби", "Шрек", "Осёл", "Фиона", "Кот в сапогах", "Тимон",
    "Пумба", "Олаф", "Стич",
)  # fmt: skip


def default_alias(taken: Collection[str]) -> str:
    """A random free name; all taken: «name 2», «name 3»… (the first round that has a free one)."""
    for n in count(1):
        free = [a if n == 1 else f"{a} {n}" for a in DEFAULT_ALIASES]
        free = [a for a in free if a not in taken]
        if free:
            return random.choice(free)
    raise AssertionError  # unreachable: count() never ends
