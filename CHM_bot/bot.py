"""
CHM BREAKER BOT — Multi-User Edition
"""

import asyncio
import logging
import os
import sys

# ── Защита от двойного запуска ────────────────────────────
LOCK_FILE = "/tmp/chm_bot.lock"

def kill_old_instance():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 9)
            logging.info(f"Убит старый процесс PID={old_pid}")
        except Exception:
            pass
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

kill_old_instance()
# ──────────────────────────────────────────────────────────

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import Config
from user_manager import UserManager
from handlers import register_handlers
from scanner_multi import MultiScanner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("chm_bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("CHM")


async def main():
    config       = Config()
    bot          = Bot(token=config.TELEGRAM_TOKEN)
    storage      = MemoryStorage()
    dp           = Dispatcher(storage=storage)
    user_manager = UserManager()
    scanner      = MultiScanner(config, bot, user_manager)

    register_handlers(dp, bot, user_manager, scanner, config)

    log.info("🚀 CHM BREAKER BOT запускается (multi-user режим)...")

    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=["message", "callback_query"]),
        scanner.run_forever(),
    )


if __name__ == "__main__":
    asyncio.run(main())
