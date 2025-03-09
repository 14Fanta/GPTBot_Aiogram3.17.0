import os
# IMPORT AIOGRAM
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
# SQLITE3
import sqlite3
# OTHERS
from dotenv import load_dotenv
from config import TOKEN_TG, MISTRAL_TOKEN
from states import *
# Mistral
from mistralai import Mistral

load_dotenv()

api_key = os.getenv('Mistral_Key_api')

model = "mistral-large-latest"

client = Mistral(api_key=MISTRAL_TOKEN)

bot = Bot(token=TOKEN_TG)
dp = Dispatcher()
db = sqlite3.connect("users.sqlite3")
cursor = db.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY, 
        tg_id INTEGER, 
        FULL_NAME TEXT
    )
""")

user_router = Router()

@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user = cursor.execute("SELECT tg_id FROM users WHERE tg_id = ?", (message.from_user.id,)).fetchone()
    if not user:
        cursor.execute("INSERT INTO users(tg_id, FULL_NAME) VALUES(?, ?)", (message.from_user.id, message.from_user.full_name))
        db.commit()
    
    await message.answer("Добро пожаловать в бота для учёбы! Ты можешь задать мне любой вопрос на тему учёбы, а я постараюсь на него ответить!\nА также ты можешь попросить меня сделать для тебя какое-то задание.\nНапиши свой запрос: ")
    
    # Инициализируем историю сообщений
    await state.update_data(chat_history=[])
    await state.set_state(waiting.waiting_a_message)

@user_router.message(waiting.waiting_a_message)
async def generator_content(msg: Message, state: FSMContext):
    
    # Проверяем, является ли сообщение командой
    if msg.text.startswith('/'):
        await msg.answer("Повторите команду.")
        await state.clear()
        return

    # Получаем историю сообщений из состояния
    user_data = await state.get_data()
    chat_history = user_data.get("chat_history", [])

    # Добавляем текущее сообщение в историю
    chat_history.append({"role": "user", "content": msg.text})

    chat_response = client.chat.complete(
        model=model,
        messages=chat_history + "Вопросы должны быть по учёбе и образованию",
        max_tokens=100,
        temperature=0.5,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0
    )

    # Добавляем ответ модели в историю
    chat_history.append({"role": "assistant", "content": chat_response.choices[0].message.content})

    # Сохраняем обновленную историю в состояние
    await state.update_data(chat_history=chat_history)

    await msg.answer(chat_response.choices[0].message.content)

@user_router.message()
async def cmd_help(message: Message):
    await message.answer(f"Ты написал: {message.text}")