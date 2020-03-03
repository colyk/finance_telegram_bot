import logging
import os

import json

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from . import db
from . import finance_requests

logging.basicConfig(
    format="\n%(asctime)s:%(levelname)s\n%(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

HELP = '''
*Budgets:*
    /getbudgets
    /addbudget
    /deletebudget
*Categories:*
    /getcategories
    /addcategories
    /deletecategories
'''


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

    def set_commands_handlers(self):
        dp = self.updater.dispatcher

        dp.add_handler(CommandHandler("start", self.on_start))
        dp.add_handler(CommandHandler("help", self.on_help))
        dp.add_handler(CommandHandler("login", self.on_login))

        dp.add_handler(CommandHandler("getbudgets", self.on_get_budgets))

        dp.add_error_handler(self.on_error)
        dp.add_handler(MessageHandler(Filters.text, self.on_text))

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
        self.reply(update, text='Provide api key:')

    def on_error(self, update, context):
        logger.warning('Update "%s" caused error "%s"', update, context.error.message)

    def on_help(self, update, context):
        self.reply(update, HELP, parse_mode=telegram.ParseMode.MARKDOWN)

    def on_text(self, update, context):
        username = update.effective_user.name
        last_cmd = context.user_data.get('last_cmd', '')
        if last_cmd == 'login':
            res = finance_requests.login(update.message.text)
            if res:
                db.save_user(username, res['api_key'])
                self.on_start(update, context)
            else:
                self.reply(update, 'Bad api key. Retry again.')

        else:
            self.reply(update,
                       f'''I don't know "{update.message.text}" command :(''')

        context.user_data['last_cmd'] = ''

    def reply(self, update, text, **kwargs):
        update.message.reply_text(text, **kwargs)

    def on_get_budgets(self, update, context):
        user = db.get_user(update.effective_user.name)
        if user is None:
            res = 'You are not logged in. Just use /login command and provide you api key.'
        else:
            res = finance_requests.get_budgets(user[1])
            res = json.dumps(res)
        self.reply(update, res)


if __name__ == "__main__":
    bot = Bot()
    bot.local_run()
