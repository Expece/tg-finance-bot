import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.markdown import text, italic
from aiogram.utils.emoji import emojize

import exceptions
import expenses
import diagram
import keyboards as kb
from categories import Categories, get_category_emoji
from config import BOT_TOKEN

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """This handler will be called when user sends `/start` or `/help` command"""
    await message.answer(text(
        emojize(f"Бот для учёта финансов :star:\n\n"),
        italic("Добавить расход: 999 продукты\n"
               "Сегодняшняя статистика: /today\n"
               "За текущий месяц: /month\n"
               "Последние внесённые расходы: /last\n"
               "Диаграмма расходов: /diagram\n"
               "Установить расход в день: /daily cash\n"
               "Категории трат: /categories\n"
               "Удалить последний расход: /del")), parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(commands=['today'])
async def show_today_expenses(message: types.Message):
    """Выводит внесенные расходы за день"""
    answer_message = expenses.get_today_statistics()
    await message.answer(answer_message)


@dp.message_handler(commands=['month'])
async def show_month_expenses(message: types.Message):
    """Выводит внесенные расходы за месяц"""
    month_statistics = expenses.get_month_statistics()
    if not month_statistics:
        answer_message = "В этом месяце нет расходов"
        await message.answer(answer_message)
        return
    answer_message = f"Расходы за месяц\nВсего: {month_statistics}"
    await message.answer(answer_message, reply_markup=kb.inline_kb_month)


@dp.message_handler(commands=['last'])
async def show_last_expenses(message: types.Message):
    """Выводит последние внесенные расходы"""
    last_expenses = expenses.last()
    if not last_expenses:
        await message.answer("Расходы еще не заведены")
        return
    answer_message = "Последние траты:\n\n" + \
                     ("\n".join([str(e.cash) + '₽' + ' ' + e.category
                                 for e in last_expenses]))
    await message.answer(answer_message)


@dp.message_handler(commands=['daily'])
async def daily_expense(message: types.Message):
    """Устанавливает базовый расход в день и выводит сообщение"""
    try:
        answer_message = expenses.set_daily_expense(message.text)
    except exceptions.UncorrectMessage as e:
        await message.reply(f'{str(e)}, напиши типо: /daily 500')
        return
    await message.answer(answer_message, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(commands=['diagram'])
async def show_diagram(message: types.Message):
    """Рисует диаграмму расходов"""
    diagram_name = diagram.save_diagram()
    if diagram_name:
        reply_markup = kb.get_diagram_keyboard(message.chat.id)
        await message.answer("Diagram", reply_markup=reply_markup)
    else:
        await message.answer("Расходы еще не заведены")


@dp.message_handler(commands=['categories'])
async def show_categories(message: types.Message):
    """Выводит категории трат"""
    categories = Categories().get_all_categories()
    answer_message = "Категории трат:\n\n-- " + \
        ("\n-- ".join([emojize(get_category_emoji(c.name)) + ' ' + c.name
                       for c in categories]))
    await message.answer(answer_message)


@dp.message_handler(commands=['del'])
async def del_expense(message: types.Message):
    """Удаляет последний расход"""
    answer_message = expenses.del_last_expense()
    await message.answer(answer_message)


@dp.message_handler()
async def add_expense(message: types.Message):
    """Добавляет расход"""
    try:
        expense = expenses.add_expense(message.text)
    except exceptions.UncorrectMessage as e:
        await message.reply(str(e)+', напиши типо: 100 такси')
        return
    answer_message = emojize(f"Добавил траты: {expense.cash}₽ на {expense.category}:white_check_mark:\n") +\
        expenses.calculate_avalible_expenses()
    await message.answer(answer_message, parse_mode=types.ParseMode.MARKDOWN)


@dp.message_handler(content_types=types.message.ContentType.ANY)
async def unknown_message(msg: types.Message):
    """Отвечает на разные типы сообщений"""
    message_text = emojize(f'Я не знаю, что с этим делать :face_with_symbols_on_mouth:,\n'
                           f'Я просто напомню что есть /help')
    await msg.reply(message_text)


@dp.callback_query_handler(text="month_expenses")
async def send_month_expenses(call: types.CallbackQuery):
    await call.message.answer(kb.month_btn_data())
    await call.answer()


@dp.callback_query_handler(kb.callback_data_diagram.filter(filter='diagram_month'))
async def send_diagram_month(call: types.CallbackQuery, callback_data: dict):
    chat_id = callback_data['chat_id']
    diagram_name = diagram.save_diagram('month')
    await bot.send_photo(chat_id=chat_id, photo=open(diagram_name, 'rb'),
                         caption='Диаграмма за месяц')
    await call.answer()
    diagram.delete_diagram()


@dp.callback_query_handler(kb.callback_data_diagram.filter(filter='diagram_year'))
async def send_diagram_year(call: types.CallbackQuery, callback_data: dict):
    chat_id = callback_data['chat_id']
    diagram_name = diagram.save_diagram('year')
    await bot.send_photo(chat_id=chat_id, photo=open(diagram_name, 'rb'),
                         caption='Диаграмма за год')
    await call.answer()
    diagram.delete_diagram()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
