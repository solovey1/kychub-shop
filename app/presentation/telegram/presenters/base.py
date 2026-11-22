from abc import ABC
from collections.abc import Callable
from typing import Any

from aiogram_i18n import I18nContext


class BasePresenter(ABC):
    pass


class Keys:
    """`keys.line_price(amount=...)` -> `i18n.get("<prefix>-line_price", amount=...)`.

    `i18n.messages.order` is a MagicProxy that appends every attribute to one shared key, so a
    stored `messages = i18n.messages.order` glues its second call onto the first. Use this."""

    def __init__(self, i18n: I18nContext, prefix: str) -> None:
        self._i18n = i18n
        self._prefix = prefix

    def __call__(self, **kwargs: Any) -> str:
        return self._i18n.get(self._prefix, **kwargs)

    def __getattr__(self, name: str) -> Callable[..., str]:
        def text(**kwargs: Any) -> str:
            return self._i18n.get(f"{self._prefix}-{name}", **kwargs)

        return text
