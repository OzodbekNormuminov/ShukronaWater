# bot/Main.py (Yuklashni eng oddiy holatga qaytarish)

import os 
import asyncio
from dotenv import load_dotenv 
# from pathlib import Path # <-- O'chirib tashlang yoki comment qiling

# ---------------- Aiogram Importlari ----------------
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

# --------------- Handler Importlari -----------------
from Client import setup_client_handlers 
from Admin import setup_admin_handlers 
from Kuryer import setup_kuryer_handlers

# ----------------- Asosiy Sozlashlar -----------------

# Agar .env Main.py bilan bir joyda bo'lsa, bu to'g'ri ishlaydi
load_dotenv() 

API_TOKEN = os.getenv("BOT_TOKEN")

if not API_TOKEN:
    print("XATO: .env faylida BOT_TOKEN topilmadi. Tokeningizni tekshiring!")
    raise ValueError("BOT_TOKEN is not set in .env file.")

# ... qolgan kod o'zgarmaydi

# ------------------ Bot Obyektlarini Yaratish ------------------
storage = MemoryStorage() 
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=storage)


# ------------------ Buyruqlar Ro'yxati ------------------
async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="admin", description="Admin paneliga kirish"),
    ]
    await bot.set_my_commands(commands)


# ------------------ Handlerlarni Bog'lash ------------------
setup_client_handlers(dp)
setup_admin_handlers(dp) 
setup_kuryer_handlers(dp)


# ------------------ Botni Ishga Tushirish ------------------
async def main():
    print("Bot ishga tushmoqda...")
    
    await set_default_commands(bot)
    
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot o'chirildi. (Keyboard Interrupt)")
    except Exception as e:
        print(f"Boshlang'ich xato: {e}")