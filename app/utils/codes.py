import secrets
from typing import Final

# no O/0/I/1: a code read aloud or typed from a screenshot is not mistaken
ALPHABET: Final = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH: Final = 5


def new_code() -> str:
    """A public number of an order or a ticket: it hides how many there are."""
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def normalize_code(text: str) -> str | None:
    """What a person typed ('№k7qx2', '#K7QX2 ') as a code, or None when it cannot be one."""
    code = text.strip().lstrip("№#").strip().upper()
    return code if len(code) == CODE_LENGTH and set(code) <= set(ALPHABET) else None


if __name__ == "__main__":
    assert all(
        len(c) == CODE_LENGTH and set(c) <= set(ALPHABET) for c in (new_code() for _ in range(500))
    )
    assert normalize_code(" №k7qx2 ") == "K7QX2" and normalize_code("57") is None
