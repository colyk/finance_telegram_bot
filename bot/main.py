import logging
import os
from datetime import date

import json

import telegram
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

import db
import finance_requests

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
*Transactions:*
    /addincome
    /addexpense
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

        dp.add_handler(CommandHandler("getcategories", self.on_get_categories))

        dp.add_handler(CommandHandler("addincome", self.on_add_income))
        dp.add_handler(CommandHandler("addexpense", self.on_add_expense))

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
        logger.warning('Update "%s" caused error "%s"',
                       update, context.error)

    def on_help(self, update, context):
        self.reply(update, HELP, parse_mode=telegram.ParseMode.MARKDOWN)

    def on_text(self, update, context):
        username = update.effective_user.name
        last_cmd = context.user_data.get('last_cmd', '')
        if last_cmd == 'login':
            res = finance_requests.login(update.message.text)
            if res:
                db.save_user(username, res['api_key'])
                context.user_data['api_key'] = res['api_key']
                self.on_start(update, context)
            else:
                context.user_data['api_key'] = ''
                self.reply(update, 'Bad api key. Retry again.')
            context.user_data['last_cmd'] = ''

        elif last_cmd == 'add_income__title':
            context.user_data['income'] = {}
            context.user_data['income']['title'] = update.message.text
            self.on_add_income__add_category(update, context)
        elif last_cmd == 'add_income__category':
            context.user_data['income']['selectedCategories'] = [
                update.message.text]
            self.on_add_income__add_amount(update, context)
        elif last_cmd == 'add_income__amount':
            context.user_data['income']['amount'] = update.message.text
            self.on_add_income__save(update, context)
            
        elif last_cmd == 'add_expense__title':
            context.user_data['expense'] = {}
            context.user_data['expense']['title'] = update.message.text
            self.on_add_expense__add_category(update, context)
        elif last_cmd == 'add_expense__category':
            context.user_data['expense']['selectedCategories'] = [
                update.message.text]
            self.on_add_expense__add_amount(update, context)
        elif last_cmd == 'add_expense__amount':
            context.user_data['expense']['amount'] = update.message.text
            self.on_add_expense__save(update, context)
        else:
            self.reply(update,
                       f'''I don't know "{update.message.text}" command :(''')

            context.user_data['last_cmd'] = ''

    def reply(self, update, text, **kwargs):
        update.message.reply_text(text, **kwargs)

    @send_typing_action
    def on_get_budgets(self, update, context):
        user = db.get_user(update.effective_user.name)
        if user is None:
            res = 'You are not logged in. Just use /login command and provide you api key.'
        else:
            res = finance_requests.get_budgets(user[1])
            res = self.parse_json(res, 'budgets', ['name', 'from', 'to'])
        self.reply(update, res, parse_mode=telegram.ParseMode.MARKDOWN)

    @send_typing_action
    def on_get_categories(self, update, context):
        user = db.get_user(update.effective_user.name)
        if user is None:
            res = 'You are not logged in. Just use /login command and provide you api key.'
        else:
            res = finance_requests.get_categories(user[1])
            res = self.parse_json(res, 'categories', ['type'])
        self.reply(update, res, parse_mode=telegram.ParseMode.MARKDOWN)

    @send_typing_action
    def on_add_income(self, update, context):
        user = db.get_user(update.effective_user.name)
        if user is None:
            self.reply(
                update, text='You are not logged in. Just use /login command and provide you api key.')
        else:
            context.user_data['last_cmd'] = 'add_income__title'
            self.reply(update, text='Provide title:')

    @send_typing_action
    def on_add_income__add_category(self, update, context):
        context.user_data['last_cmd'] = 'add_income__category'
        user = db.get_user(update.effective_user.name)
        api_key = user[1]

        categories = finance_requests.get_categories(api_key)['categories']
        categories = map(lambda cat: cat['type'], categories)
        menu_keyboard = [categories]
        menu_markup = telegram.ReplyKeyboardMarkup(
            menu_keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        self.updater.bot.sendMessage(
            chat_id=update.message.chat_id,
            text="Pick a category:",
            reply_markup=menu_markup,
        )

    @send_typing_action
    def on_add_income__add_amount(self, update, context):
        context.user_data['last_cmd'] = 'add_income__amount'
        self.reply(update, text='Provide amount:')

    @send_typing_action
    def on_add_income__save(self, update, context):
        user = db.get_user(update.effective_user.name)
        api_key = user[1]
        income = context.user_data['income']
        income['api_key'] = api_key

        today = date.today()
        income['date'] = today.strftime('%Y-%m-%d')
        income['year'] = 2020
        income['month'] = 1
        income['day'] = 1
        income['monthDay'] = 1

        income['type'] = 'income'

        res = finance_requests.post_transaction(income)
        if res is None:
            self.reply(update, text='Error!')
        else:
            self.reply(update, text='Created!')            

 
    @send_typing_action
    def on_add_expense(self, update, context):
        user = db.get_user(update.effective_user.name)
        if user is None:
            self.reply(
                update, text='You are not logged in. Just use /login command and provide you api key.')
        else:
            context.user_data['last_cmd'] = 'add_expense__title'
            self.reply(update, text='Provide title:')

    @send_typing_action
    def on_add_expense__add_category(self, update, context):
        context.user_data['last_cmd'] = 'add_expense__category'
        user = db.get_user(update.effective_user.name)
        api_key = user[1]

        categories = finance_requests.get_categories(api_key)['categories']
        categories = map(lambda cat: cat['type'], categories)
        menu_keyboard = [categories]
        menu_markup = telegram.ReplyKeyboardMarkup(
            menu_keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        self.updater.bot.sendMessage(
            chat_id=update.message.chat_id,
            text="Pick a category:",
            reply_markup=menu_markup,
        )

    @send_typing_action
    def on_add_expense__add_amount(self, update, context):
        context.user_data['last_cmd'] = 'add_expense__amount'
        self.reply(update, text='Provide amount:')

    @send_typing_action
    def on_add_expense__save(self, update, context):
        user = db.get_user(update.effective_user.name)
        api_key = user[1]
        expense = context.user_data['expense']
        expense['api_key'] = api_key

        today = date.today()
        expense['date'] = today.strftime('%Y-%m-%d')
        expense['year'] = 2020
        expense['month'] = 1
        expense['day'] = 1
        expense['monthDay'] = 1

        expense['type'] = 'expense'

        res = finance_requests.post_transaction(expense)
        if res is None:
            self.reply(update, text='Error!')
        else:
            self.reply(update, text='Created!')            

    def parse_json(self, json: dict, root: str, keys: list) -> str:
        res = '*' + root.title() + '*:'

        with_title = len(keys) > 1
        for item in json[root]:
            for idx, key in enumerate(keys):
                if with_title and idx == 0:
                    res += '\n_' + item[key] + '_:'
                else:
                    res += '\n- ' + item[key]
        return res


if __name__ == "__main__":
    bot = Bot()
    bot.local_run()
