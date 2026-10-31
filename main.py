"""Private chat bridge for AstrBot.

AstrBot keeps every private conversation isolated. This plugin records the last
messages of each private contact and injects a short digest of *other* chats
into the current request, so the bot can answer questions like "what did the
other friend just say?" without leaking anything into group chats.

Data lives in ``<astrbot data>/plugin_data/astrbot_plugin_private_bridge``.
"""

import json
import time
from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.provider.entities import ProviderRequest

try:
    from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

    BASE = Path(get_astrbot_plugin_data_path()) / "astrbot_plugin_private_bridge"
except Exception:  # pragma: no cover - very old AstrBot builds
    BASE = Path("data/plugin_data/astrbot_plugin_private_bridge")

STORE = BASE / "chats.json"
MAX_PER_CHAT = 20


@register(
    "astrbot_plugin_private_bridge",
    "dsh",
    "让 bot 知道其他私聊好友最近说了什么",
    "0.1.1",
)
class PrivateBridge(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.conf = config or {}
        BASE.mkdir(parents=True, exist_ok=True)
        self.chats: dict[str, dict] = {}
        try:
            if STORE.is_file():
                self.chats = json.loads(STORE.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("[private_bridge] load failed: %s", exc)

    def _save(self) -> None:
        try:
            STORE.write_text(
                json.dumps(self.chats, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("[private_bridge] save failed: %s", exc)

    @filter.event_message_type(filter.EventMessageType.PRIVATE_MESSAGE, priority=200)
    async def record(self, event: AstrMessageEvent):
        try:
            uid = str(event.get_sender_id())
            name = event.get_sender_name() or uid
            text = (event.message_str or "").strip()
            if not uid or not text:
                return
            info = self.chats.setdefault(uid, {"name": name, "msgs": []})
            info["name"] = name
            info["msgs"].append({"t": time.strftime("%H:%M"), "text": text[:200]})
            info["msgs"] = info["msgs"][-MAX_PER_CHAT:]
            self._save()
        except Exception as exc:
            logger.debug("[private_bridge] record failed: %s", exc)

    @filter.on_llm_request(priority=-500)
    async def inject(self, event: AstrMessageEvent, req: ProviderRequest):
        try:
            if not event.is_private_chat():
                return
            me = str(event.get_sender_id())
            lines = []
            contacts = []
            for uid, info in self.chats.items():
                if uid == me:
                    continue
                name = info.get("name", uid)
                contacts.append(f"{name}({uid})")
                for m in info.get("msgs", [])[-6:]:
                    lines.append(f"- {name}({uid}) {m['t']}: {m['text']}")
            if not contacts:
                return
            block = (
                "\n\n[Other private contacts you know]\n"
                + ", ".join(contacts)
                + "\n[Their recent messages - background only]\n"
                + ("\n".join(lines[-12:]) if lines else "(no new messages)")
                + "\nMention these naturally when asked; do not volunteer them otherwise.\n"
            )
            req.system_prompt = (req.system_prompt or "") + block
        except Exception as exc:
            logger.debug("[private_bridge] inject failed: %s", exc)
