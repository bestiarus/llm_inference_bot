from os import environ

from loguru import logger
from openai import OpenAIError
from vkbottle import Bot, API
from vkbottle.bot import Message
from vkbottle.framework.labeler import BotLabeler

from dialogue_tracker import DialogueTracker

_VK_API = API(environ.get("VK_API_TOKEN"))
_VK_BOT_LABELER = BotLabeler()
_DIALOG_TRACKER = DialogueTracker()

_google_spreadsheet_id = environ.get("GOOGLE_SPREADSHEET_ID", None)
if _google_spreadsheet_id is not None:
    from google_sheets_wrapper import GoogleSheetsWrapper

    logger.info(f"Using Google Sheets to track usage")
    _GOOGLE_SHEETS_WRAPPER = GoogleSheetsWrapper(_google_spreadsheet_id)
else:
    logger.info(f"No usage tracking")
    _GOOGLE_SHEETS_WRAPPER = None


async def get_chat_history(peer_id: int, count: int = 50) -> list[dict]:
    """Получает историю сообщений из чата"""
    try:
        logger.info(f"Getting chat history for peer_id: {peer_id}, count: {count}")
        
        # Получаем историю сообщений
        history_response = await _VK_API.messages.get_history(
            peer_id=peer_id,
            count=count,
            rev=0  # В обратном хронологическом порядке (новые сначала)
        )
        
        messages = history_response.items
        logger.info(f"Retrieved {len(messages)} messages from VK API")
        
        # Получаем информацию о пользователях для отображения имен
        user_ids = set()
        for msg in messages:
            if msg.from_id > 0:  # Исключаем сообщения от групп
                user_ids.add(msg.from_id)
        
        users_info = {}
        if user_ids:
            logger.info(f"Getting user info for {len(user_ids)} users")
            users = await _VK_API.users.get(user_ids=list(user_ids))
            for user in users:
                users_info[user.id] = f"{user.first_name} {user.last_name}"
        
        # Формируем контекст чата
        chat_context = []
        for msg in reversed(messages):  # Переворачиваем для хронологического порядка
            if msg.from_id > 0:  # Только сообщения от пользователей
                user_name = users_info.get(msg.from_id, f"User{msg.from_id}")
                chat_context.append({
                    "user_id": msg.from_id,
                    "user_name": user_name,
                    "text": msg.text,
                    "timestamp": msg.date
                })
        
        logger.info(f"Processed {len(chat_context)} user messages for context")
        return chat_context
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return []


_HELP_MESSAGE = """Список команд:
- /help -- Помощь
- /role <role> -- Установить кастомную роль
- /reset -- Сбросить роль на стандартную, очистить историю

Максимальное число сообщений в истории: {messages_in_history}, время жизни истории: {max_alive_dialogue} секунд.
Текущая роль: '{role}'
Если бот долго не отвечает, вероятно, OpenAI API перегружено, попробуйте позже.
Если сообщение выводится не до конца, то превышен лимит по токенам, сбросьте историю.
По всем вопросам: @boss
"""

_OPENAI_ERROR_MESSAGE = (
    "Какая-то ошибка на сервере OpenAI, скорее всего перегружен другими запросами 🫠. "
    "Повторите запрос позже или попробуйте сбросить историю с помощью `/reset`"
)
_SYSTEM_ERROR_MESSAGE = (
    "Что-то пошло не так 🫠. Попробуйте сбросить историю с помощью `/reset` или напишите @spirin.egor 🤗!"
)


@_VK_BOT_LABELER.message(command="help")
async def help_message(message: Message):
    user_id = message.from_id
    help_msg = _HELP_MESSAGE.format(role=_DIALOG_TRACKER.get_role(user_id), **_DIALOG_TRACKER.config)
    await message.answer(help_msg)


@_VK_BOT_LABELER.message(command="reset")
async def reset(message: Message):
    user_id = message.from_id
    _DIALOG_TRACKER.reset(user_id)
    await message.answer("Роль сброшена на стандартную, история сброшена")


@_VK_BOT_LABELER.message()
async def handle_message(message: Message):
    user_id = message.from_id
    text = message.text
    peer_id = message.peer_id

    # Определяем chat_id для групповых чатов
    if peer_id >= 2000000000:
        chat_id = peer_id - 2000000000
        logger.info(f'Групповой чат: peer_id={peer_id}, chat_id={chat_id}')
    else:
        chat_id = None
        logger.info(f'Личное сообщение или беседа: peer_id={peer_id}')

    logger.info(f"Получено сообщение от {user_id} в чате {peer_id}: {text[:50]}...")

    try:
        # Получаем информацию о боте
        bot_info = await _VK_API.users.get()
        bot_id = bot_info[0].id
        bot_name = bot_info[0].first_name.lower()
        logger.info(f"Bot ID: {bot_id}, Bot name: {bot_name}")
        bot_mentioned = False
        if f"@id{bot_id}" in text or f"@club{bot_id}" in text:
            bot_mentioned = True
            logger.info(f"Bot mentioned by ID: @id{bot_id}")
        elif f"@{bot_name}" in text.lower():
            bot_mentioned = True
            logger.info(f"Bot mentioned by name: @{bot_name}")
        elif text.startswith("/"):
            bot_mentioned = True
            logger.info(f"Command detected: {text}")
        logger.info(f"Bot mentioned: {bot_mentioned}")
        if not bot_mentioned:
            logger.info(f"Ignoring message - bot not mentioned")
            return
    except Exception as e:
        logger.error(f"Error checking bot mention: {e}")
        bot_mentioned = True

    if text.startswith("/role"):
        command, argument = text.split(maxsplit=1)
        if not argument:
            await message.answer("Необходимо указать роль: /role <role>")
            return
        _DIALOG_TRACKER.set_role(user_id, argument)
        await message.answer("Роль установлена, история сброшена")
        return

    try:
        logger.info(f"Processing message with context for user {user_id}")
        chat_context = await get_chat_history(peer_id, count=50)
        if not chat_context:
            logger.warning(f"Не удалось получить историю сообщений для peer_id={peer_id} (chat_id={chat_id}). Возможно, нет доступа к истории чата.")
            #await message.answer("⚠️ Не удалось получить историю сообщений чата. Проверьте права доступа бота.")
            return
        logger.info(f"Retrieved {len(chat_context)} messages from chat history")
        answer, total_tokens = await _DIALOG_TRACKER.on_message_with_context(
            message.text, user_id, chat_context
        )
        user_info = (await _VK_API.users.get(user_id))[0]
        user_name = f"{user_info.last_name} {user_info.first_name}"
        if _GOOGLE_SHEETS_WRAPPER is not None:
            _GOOGLE_SHEETS_WRAPPER.increase_user_usage(user_id, user_name, total_tokens)
        logger.info(f"Generated response for user {user_id}: {answer[:50]}...")
    except OpenAIError as e:
        logger.warning(f"OpenAI API error: {e}")
        answer = _OPENAI_ERROR_MESSAGE
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        answer = _SYSTEM_ERROR_MESSAGE
    await message.answer(answer)


def main():
    logger.disable("vkbottle")
    logger.info(f"Starting VK bot")
    bot = Bot(api=_VK_API, labeler=_VK_BOT_LABELER)
    logger.info(f"Success?")
    bot.run_forever()


if __name__ == "__main__":
    main()
