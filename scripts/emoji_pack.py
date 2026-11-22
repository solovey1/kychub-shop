"""Upload assets/emoji as a custom emoji set. Run by hand:
    uv run python scripts/emoji_pack.py --owner <telegram user id> [--update]
Writes assets/emoji/ids.json {emoji: custom_emoji_id}. Never prints the token.
"""
import argparse
import asyncio
import json
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, InputSticker

from app.providers.infrastructure.app import create_app_config

DIR = Path(__file__).resolve().parent.parent / "assets" / "emoji"


async def main(owner: int, update: bool) -> None:
    emoji_map = json.loads((DIR / "map.json").read_text("utf-8"))
    async with Bot(create_app_config().telegram.bot_token.get_secret_value()) as bot:
        set_name = f"farmhub_by_{(await bot.get_me()).username}"

        def sticker(emoji: str, item: dict) -> InputSticker:
            return InputSticker(
                sticker=FSInputFile(DIR / "png" / item["file"].replace(".svg", ".png")),
                format="static",
                emoji_list=[emoji],
            )

        if update:
            have = {s.emoji for s in (await bot.get_sticker_set(set_name)).stickers}
            for emoji, item in emoji_map.items():
                if emoji not in have:
                    await bot.add_sticker_to_set(owner, set_name, sticker(emoji, item))
        else:
            await bot.create_new_sticker_set(
                owner,
                set_name,
                "FarmHub",
                [sticker(e, i) for e, i in emoji_map.items()],
                sticker_type="custom_emoji",
            )
        stickers = (await bot.get_sticker_set(set_name)).stickers
        ids = {s.emoji: s.custom_emoji_id for s in stickers}
        (DIR / "ids.json").write_text(json.dumps(ids, ensure_ascii=False, indent=1), "utf-8")
        print(f"{set_name}: {len(ids)} emoji -> assets/emoji/ids.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", type=int, required=True)
    ap.add_argument("--update", action="store_true")
    a = ap.parse_args()
    asyncio.run(main(a.owner, a.update))
