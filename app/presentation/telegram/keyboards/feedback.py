from typing import Callable

from aiogram.types import InlineKeyboardMarkup

from app.presentation.telegram.callbacks.feedback import CDRate, CDTip
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.common import button, markup

TIP_AMOUNTS = (1, 3, 5)

# a translator: `i18n.get` in handlers, the recipient translator in notifications
Tr = Callable[..., str]


def rate_keyboard(tr: Tr, order_id: int, *, rated: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not rated:
        rows.append([button(str(n), CDRate(id=order_id, score=n)) for n in range(1, 6)])
    rows.append([button(tr("buttons-tip"), CDTip(id=order_id))])
    return markup(rows)


def tip_keyboard(tr: Tr, order_id: int, token: str) -> InlineKeyboardMarkup:
    amounts = [button(f"${a}", CDTip(id=order_id, c=a * 100, t=token)) for a in TIP_AMOUNTS]
    return markup(
        [
            amounts,
            [button(tr("buttons-tip_custom"), CDTip(id=order_id, c=-1, t=token))],
            [button(tr("buttons-back"), CDRate(id=order_id))],
        ]
    )


def tip_cancel_keyboard(tr: Tr, order_id: int) -> InlineKeyboardMarkup:
    return markup([[button(tr("buttons-back"), CDTip(id=order_id))]])


def done_keyboard(tr: Tr) -> InlineKeyboardMarkup:
    return markup([[button(tr("buttons-menu"), CDMenu())]])
