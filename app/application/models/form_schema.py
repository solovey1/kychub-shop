import re
from enum import StrEnum
from typing import Optional, Self

from pydantic import BaseModel, model_validator


class FieldType(StrEnum):
    text = "text"
    email = "email"
    number = "number"
    choice = "choice"
    login = "login"
    file = "file"


_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_NUMBER_RE = re.compile(r"^-?\d+([.,]\d+)?$")


class FormField(BaseModel):
    key: str
    label: dict[str, str]
    type: FieldType
    required: bool = True
    regex: Optional[str] = None
    options: Optional[list[str]] = None
    hidden_from_executor: bool = False

    @model_validator(mode="after")
    def _check(self) -> Self:
        if not _KEY_RE.match(self.key):
            raise ValueError(f"bad field key: {self.key!r}")
        if "ru" not in self.label:
            raise ValueError("label must contain 'ru'")
        if self.regex is not None:
            try:
                re.compile(self.regex)
            except re.error as e:
                raise ValueError(f"bad regex: {e}") from e
        if self.type is FieldType.choice and not self.options:
            raise ValueError("choice field requires options")
        return self

    def validate_value(self, raw: str) -> str:
        value = raw.strip()
        if not value:
            if self.required:
                raise ValueError("value is required")
            return value
        if self.type is FieldType.email and not _EMAIL_RE.match(value):
            raise ValueError("invalid email")
        if self.type is FieldType.number and not _NUMBER_RE.match(value):
            raise ValueError("invalid number")
        if self.type is FieldType.choice and value not in (self.options or []):
            raise ValueError("value is not among options")
        if self.regex is not None and not re.fullmatch(self.regex, value):
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
