from app.const import MESSAGES_SOURCE_DIR

LOCALES = ("ru", "en", "uk")


def _keys(locale: str) -> set[str]:
    keys = set()
    for f in (MESSAGES_SOURCE_DIR / locale).glob("*.ftl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            if line and not line[0].isspace() and "=" in line and not line.startswith("#"):
                keys.add(line.split("=", 1)[0].strip())
    return keys


def test_all_locales_have_same_keys() -> None:
    base = _keys("ru")
    assert base, "ru locale is empty"
    for loc in LOCALES[1:]:
        assert _keys(loc) == base, f"{loc} differs: {_keys(loc) ^ base}"
