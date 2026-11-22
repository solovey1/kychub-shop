from .base import EnvSettings


class CommonConfig(EnvSettings, env_prefix="COMMON_"):
    admin_chat_id: int
    owner_ids: str = ""  # comma separated Telegram ids
    test_payments: bool = False
    custom_emoji: bool = True  # swap plain emoji for the FarmHub custom set

    @property
    def owner_id_set(self) -> frozenset[int]:
        return frozenset(int(x) for x in self.owner_ids.split(",") if x.strip())
