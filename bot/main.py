import logging
import os

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from . import db
from . import finance_requests

logging.basicConfig(
    format="\n%(asctime)s:%(levelname)s\n%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def send_typing_action(func):
    def wrapper(self, update, context):
        context.bot.send_chat_action(
            chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING
        )
        func(self, update, context)

    return wrapper


class Bot:
    def __init__(self):
        self.token = os.getenv("telegram_token")
        if self.token is None:
            logger.error('Set "telegram_token" environment variable.')
            logger.error("export telegram_token=example_token")
            exit(os.EX_CONFIG)

        self.updater = Updater(self.token, use_context=True)
        self.set_commands_handlers()

    def local_run(self):
        self.updater.start_polling()
        self.updater.idle()

    def web_run(self):
        port = int(os.environ.get("PORT", 5000))
        self.updater.start_webhook(
            listen="0.0.0.0", port=port, url_path=self.token,
        )
        self.updater.bot.setWebhook(
            "https://finance-telegram.herokuapp.com/{}".format(self.token)
        )
        self.updater.idle()

    def text_to_channel(self, chat_id, text):
        self.updater.bot.sendMessage(chat_id=chat_id, text=text)

    def set_commands_handlers(self):
        dp = self.updater.dispatcher

        dp.add_handler(CommandHandler("start", self.on_start))
        dp.add_handler(CommandHandler("login", self.on_login))

        dp.add_error_handler(self.on_error)
        dp.add_handler(MessageHandler(Filters.text, self.on_unknown))

    @send_typing_action
    def on_start(self, update, context):
        context.user_data['last_cmd'] = ''
        user = db.get_user(update.effective_user.name)
        if user is None:
            res = 'You are not logged in. Just use /login command and provide you api key.'
        else:
            res = 'You are logged in. Use /help to see available commands.'

        update.message.reply_text(
            f'Hi, {update.effective_user.full_name}! \n{res}')

    def on_login(self, update, context):
        context.user_data['last_cmd'] = 'login'
        update.message.reply_text('Provide api key:')

    def on_error(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def on_unknown(self, update, context):
        if context.user_data.get('last_cmd', '') == 'login':
            update.message.reply_text(
                f'''Provide api key''')
            finance_requests.login(update.message.text)
            
        else:
            update.message.reply_text(
                f'''I don't know "{update.message.text}" command :(''')

        context.user_data['last_cmd'] = ''


if __name__ == "__main__":
    bot = Bot()
    bot.local_run()
