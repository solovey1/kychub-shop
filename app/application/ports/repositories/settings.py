from typing import Any, Protocol


class SettingsGateway(Protocol):
    async def get(self, key: str, default: Any) -> Any:
        """The stored JSON value, or `default` when the key is not set."""
