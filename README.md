# ChatGPT bot

Simple chatbot using Groq's [public API](https://groq.com/)

## Pre-requisites

1. Create an account on [Groq](https://groq.com/)
2. Create an API key and add it to your environment variables as GROQ_API_KEY`
3. Install the dependencies using `pip install -r requirements.txt`

## VK bot

To run the [VK](https://vk.com) bot, you need to create a VK group and generate API key in settings.
Navigate to API Usage and create `access token` with `community messages` permission.
Add the token to your environment variables as `VK_API_TOKEN`.

To start the bot run:
```shell
python vk_bot.py
```

Use `/help` to see the list of available commands.

### Features

- **Chat Context**: The bot now receives the last 50 messages from the chat as context when responding, allowing it to understand the conversation flow and respond more appropriately.
- **Mention-based Responses**: The bot only responds when mentioned using `@bot_name` or `@id{bot_id}`.
- **Role Management**: Users can set custom roles using `/role <role>` command.
- **History Reset**: Use `/reset` to clear conversation history and reset to default role.

VK Bot also can log all usage statistic to Google Sheets.
Follow [documentation](https://developers.google.com/sheets/api/quickstart/python) to set up API.
You will need to install additional dependencies from [`requirements-google.txt`](requirements-google.txt),
place the file `credentials.json` in the root of the project, and set the environment variable `GOOGLE_SPREADSHEET_ID`.

## Telegram bot

Telegram bot only works in [inline mode](https://telegram.org/blog/inline-bots)
and only for users specified in `tg_id_whitelist.txt`.

Create the bot via [`@BotFather`](https://t.me/BotFather),
enable inline mode and inline feedback.
Add the generated token to your environment variables as `TG_API_TOKEN`.


To start the bot run:
```shell
python telegram_bot.py
```
