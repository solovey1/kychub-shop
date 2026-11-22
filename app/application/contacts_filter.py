"""Contact sharing in order chats: the deal stays in the shop, so the buyer and the executor may
not pass each other a username, a link, an e-mail, a phone number or the name of a messenger.

`find_contact(text)` returns what kind of thing was found (never the text itself, it is only for
the journal) or None. The lists below are short on purpose: a normal conversation («2 accounts»,
«code 123456», «steam guard») must pass. Run this file for the self-check."""

import re
from typing import Final

# Longer words: matched from the start of a word, so any ending passes («телеграму»).
LONG_WORDS: Final = (
    "телеграм",
    "телега",
    "ватсап",
    "вотсап",
    "вацап",
    "вайбер",
    "дискорд",
    "инстаграм",
    "инста",
    "скайп",
    "в личку",
    "в личке",
    "в личные",
    "в лс",
)
LONG_WORDS_LATIN: Final = (
    "telegram",
    "whatsapp",
    "watsapp",
    "viber",
    "signal",
    "discord",
    "instagram",
    "skype",
)
# Short words: only as a whole word, or «tg» would be found inside other words.
SHORT_WORDS: Final = ("тг", "инст", "лс")
SHORT_WORDS_LATIN: Final = ("tg", "tlg", "insta")
TLDS: Final = "com|ru|net|org|me|io|ua|gg|xyz|link|cc|by|kz|su|info|app|tv"

# Look-alike letters: «тeлeгpaм» with Latin e, p, a is still «телеграм».
_CYR_TO_LAT: Final = str.maketrans("аеорсухкмтн", "aeopcyxkmth")
_LAT_TO_CYR: Final = str.maketrans("aeopcyxkmthb", "аеорсухкмтнв")

_START: Final = r"(?<![^\W_])"  # not in the middle of a word
_LETTER: Final = r"[^\W\d_]"
_SPACED: Final = re.compile(rf"(?<!\w){_LETTER}(?:[\s.\-_*]+{_LETTER}){{2,}}(?!\w)")
_SEPARATORS: Final = re.compile(r"[\s.\-_*]+")
_USERNAME: Final = re.compile(r"(?<![\w@.])@[a-z0-9_]{5,}")
_EMAIL: Final = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}")
_DOMAIN: Final = re.compile(rf"(?<![\w-])[\w-]+\.(?:{TLDS})(?![^\W_])")
_SPACED_LINK: Final = re.compile(r"(?<![^\W_])(?:tme|wame|vkcom)\s*/")
_PHONE: Final = re.compile(r"(?<![\d+])\+?\d(?:[\s().\-]{0,2}\d){9,14}(?!\d)")
_BAD_URL: Final = re.compile(r"(?:https?://|www\.)\S+")


def _words(items: tuple[str, ...], *, whole: bool) -> re.Pattern[str]:
    tail = r"(?![^\W_])" if whole else ""
    return re.compile(_START + "(?:" + "|".join(re.escape(i) for i in items) + ")" + tail)


_LONG_CYR: Final = _words(LONG_WORDS, whole=False)
_LONG_LAT: Final = _words(LONG_WORDS_LATIN, whole=False)
_SHORT_CYR: Final = _words(SHORT_WORDS, whole=True)
_SHORT_LAT: Final = _words(SHORT_WORDS_LATIN, whole=True)


def _check(low: str) -> str | None:
    lat = low.translate(_CYR_TO_LAT)
    cyr = low.translate(_LAT_TO_CYR)
    if _BAD_URL.search(low):
        return "link"
    if _USERNAME.search(low):
        return "username"
    if _EMAIL.search(low):
        return "email"
    if _DOMAIN.search(lat) or _SPACED_LINK.search(lat):
        return "link"
    if _PHONE.search(low):
        return "phone"
    for pattern, text in (
        (_LONG_CYR, cyr),
        (_SHORT_CYR, cyr),
        (_LONG_LAT, lat),
        (_SHORT_LAT, lat),
    ):
        if found := pattern.search(text):
            return f"word:{found.group()}"
    return None


def find_contact(text: str | None) -> str | None:
    """What kind of contact the text carries ('username', 'link', 'email', 'phone',
    'word:...'), or None."""
    if not text:
        return None
    low = text.lower().replace("ё", "е")
    # «т е л е г р а м», «t . m e / nick»: the same text with spaced-out letters glued
    glued = _SPACED.sub(lambda m: _SEPARATORS.sub("", m.group()), low)
    return _check(low) or (_check(glued) if glued != low else None)


if __name__ == "__main__":
    blocked = [
        "@vasya_pupkin",
        "напиши мне t.me/vasya",
        "t . m e / nick",
        "+7 999 123-45-67",
        "8 (999) 123 45 67",
        "пиши в тг",
        "давай в вайбер",
        "write me in Telegram",
        "т е л е г р а м",
        "тeлeгpaм",
        "mail me: a.b@gmail.com",
        "https://example.org/x",
        "vk.com/id1",
        "напиши в лс",
        "whatsapp",
    ]
    allowed = [
        "заказ на 2 аккаунта",
        "код 123456",
        "steam guard",
        "пароль Zt9!kLm2, почта готова",
        "Готово, проверяй. Если что, пиши сюда",
        "аккаунт 5 из 10 готов",
        "",
    ]
    for line in blocked:
        assert find_contact(line), line
    for line in allowed:
        assert find_contact(line) is None, (line, find_contact(line))
    print("ok")  # noqa: T201
