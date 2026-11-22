import re
from enum import StrEnum
from typing import Optional, Self

from pydantic import BaseModel, PrivateAttr, model_validator


class FieldType(StrEnum):
    text = "text"
    email = "email"
    number = "number"
    choice = "choice"
    login = "login"
    file = "file"


_KEY_RE = re.compile(r"[a-z][a-z0-9_]{0,31}")
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_NUMBER_RE = re.compile(r"-?[0-9]+(\.[0-9]+)?", re.ASCII)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
_MAX_REGEX_LEN = 256
_MAX_HINT_LEN = 200
_MAX_PLACEHOLDER_LEN = 64  # Telegram limit of input_field_placeholder
_MAX_FILES = 10
_MAX_FILE_ID_LEN = 256


def split_files(value: str) -> list[str]:
    """The file ids of a `file` answer: one id, or several joined with a newline."""
    return [x for x in (p.strip() for p in value.split("\n")) if x]


def join_files(file_ids: list[str]) -> str:
    return "\n".join(file_ids)


class FormField(BaseModel):
    key: str
    label: dict[str, str]
    type: FieldType
    required: bool = True
    regex: Optional[str] = None
    options: Optional[list[str]] = None
    hidden_from_executor: bool = False
    hint: Optional[dict[str, str]] = None  # shown under the question, per locale
    placeholder: Optional[dict[str, str]] = None  # grey text of the input field, per locale
    max_length: int = 512
    max_files: int = 1  # only for type=file; the answer is the ids joined with a newline
    _compiled: Optional[re.Pattern[str]] = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if not _KEY_RE.fullmatch(self.key):
            raise ValueError(f"bad field key: {self.key!r}")
        if "ru" not in self.label:
            raise ValueError("label must contain 'ru'")
        if not 1 <= self.max_length <= 4096:
            raise ValueError("max_length must be 1..4096")
        if not 1 <= self.max_files <= _MAX_FILES:
            raise ValueError(f"max_files must be 1..{_MAX_FILES}")
        self._check_texts()
        if self.regex is not None:
            if len(self.regex) > _MAX_REGEX_LEN:
                raise ValueError(f"regex longer than {_MAX_REGEX_LEN}")
            try:
                self._compiled = re.compile(self.regex)
            except re.error as e:
                raise ValueError(f"bad regex: {e}") from e
        if self.type is FieldType.choice and not self.options:
            raise ValueError("choice field requires options")
        return self

    def _check_texts(self) -> None:
        for texts, limit in ((self.hint, _MAX_HINT_LEN), (self.placeholder, _MAX_PLACEHOLDER_LEN)):
            if texts and any(len(t) > limit for t in texts.values()):
                raise ValueError(f"hint/placeholder longer than {limit}")

    def _check_type(self, value: str) -> str:
        if self.type is FieldType.email and not _EMAIL_RE.fullmatch(value):
            raise ValueError("invalid email")
        if self.type is FieldType.number:
            value = value.replace(",", ".", 1)
            if not _NUMBER_RE.fullmatch(value):
                raise ValueError("invalid number")
        if self.type is FieldType.choice and value not in (self.options or []):
            raise ValueError("value is not among options")
        return value

    def _validate_files(self, raw: str) -> str:
        files = split_files(raw)
        if not files:
            if self.required:
                raise ValueError("value is required")
            return ""
        if len(files) > self.max_files:
            raise ValueError("too many files")
        if any(len(f) > _MAX_FILE_ID_LEN or _CONTROL_RE.search(f) for f in files):
            raise ValueError("value is too long")
        return join_files(files)

    def validate_value(self, raw: str) -> str:
        if self.type is FieldType.file:
            return self._validate_files(raw)
        if len(raw) > self.max_length + 64:  # cheap bound before any further work
            raise ValueError("value is too long")
        if _CONTROL_RE.search(raw):
            raise ValueError("control characters are not allowed")
        value = raw.strip()
        if len(value) > self.max_length:
            raise ValueError("value is too long")
        if not value:
            if self.required:
                raise ValueError("value is required")
            return value
        value = self._check_type(value)
        if self._compiled is not None and not self._compiled.fullmatch(value):
            raise ValueError("value does not match the required format")
        return value


class FormSchema(BaseModel):
    fields: list[FormField]

    @model_validator(mode="after")
    def _unique_keys(self) -> Self:
        keys = [f.key for f in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate field keys")
        return self

    def validate_answer(self, key: str, raw: str) -> str:
        for f in self.fields:
            if f.key == key:
                return f.validate_value(raw)
        raise ValueError(f"unknown field: {key}")
