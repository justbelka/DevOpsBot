import os, re, logging, paramiko, psycopg2, glob
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler


TEXT_COMMANDS = '''Выбери команду:
/find_email - Найти адреса электронной почты в тексте
/find_phone_number - Найти все телефоны в тексте

/help - Вернуться в главное меню
'''

PASSWORD_COMMANDS = '''Чтобы проверить пароль на защищённость используй команду:
/verify_password

/help - Вернуться в главное меню
'''

LINUX_COMMANDS = '''Выбери команду:
/get_release - Вывести информацию о релизе
/get_uname - Вывести информацию об архитектуре процессора, имени хоста системы и версии ядра
/get_uptime - Вывести информацию о времени работы

/get_df - Вывести информацию о состоянии файловой системы
/get_free - Вывести информацию о состоянии оперативной памяти
/get_mpstat - Вывести информацию о производительности системы
/get_w - Вывести информацию о работающих в данной системе пользователях

/get_auths - Вывести последние 10 входов в систему
/get_critical - Вывести последние 5 критических события
/get_ps - Вывести информацию о запущенных процессах
/get_ss - Вывести информацию об используемых портах
/get_apt_list - Вывести информацию об установленных пакетах
/get_some_package - Вывести информацию о конкретном пакете

/help - Вернуться в главное меню
'''

DB_COMMANDS = '''Выбери команду:
/get_emails - Вывести все email-адреса из базы
/get_phone_numbers - Вывести все номера телефонов из базы
/get_repl_log - Вывести логи о репликации
'''


load_dotenv(dotenv_path = os.path.join(os.path.dirname(__file__), '../../.env'))
TOKEN = os.getenv('TOKEN')
RM_HOST = os.getenv('RM_HOST')
RM_USER = os.getenv('RM_USER')
RM_PASSWORD = os.getenv('RM_PASSWORD')

# Подключаем логирование
logging.basicConfig(
    filename='AlexBelokrylov.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


EMAIL_INPUT, PHONE_INPUT, PASSWORD_INPUT, PACKAGE_INPUT = range(4)


def db_execute(command, select=True):
    result = []
    conn_params = {
        'host': os.getenv('DB_HOST'),
        'database': os.getenv('DB_DATABASE'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': os.getenv('DB_PORT')
    }
    conn = None
    try:
        conn = psycopg2.connect(**conn_params)
        cursor = conn.cursor()
        cursor.execute(command)
        if select:
            rows = cursor.fetchall()
            for row in rows:
                result.append(row[1])
        else:
            conn.commit()
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
    return result


def system(command, host=RM_HOST):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(host, username=RM_USER, password=RM_PASSWORD)
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode()
        result = f"Server: {host}\n{output}"
        client.close()
    except Exception as e:
        result = f"Failed to connect to {host}: {e}"
    return result


def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton('Поиск в тексте', callback_data='text_commands')], 
        [InlineKeyboardButton('Проверка пароля', callback_data='password_commands')],
        [InlineKeyboardButton('Linux-мониторинг', callback_data='linux_commands')],
        [InlineKeyboardButton('База данных', callback_data='db_commands')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    user = update.effective_user
    update.message.reply_text(f'Привет, {user.full_name}!\nВыбери команду:', reply_markup=reply_markup)
    return ConversationHandler.END
    

def button(update: Update, context):
    query = update.callback_query
    query.answer()

    if query.data == 'back':
        keyboard = [
            [InlineKeyboardButton('Поиск в тексте', callback_data='text_commands')], 
            [InlineKeyboardButton('Проверка пароля', callback_data='password_commands')],
            [InlineKeyboardButton('Linux-мониторинг', callback_data='linux_commands')],
            [InlineKeyboardButton('База данных', callback_data='db_commands')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        user = update.effective_user
        query.edit_message_text(f'Привет, {user.full_name}!\nВыбери команду:', reply_markup=reply_markup)
    elif query.data == 'text_commands':
        query.message.reply_text(TEXT_COMMANDS)
    elif query.data == 'password_commands':
        query.message.reply_text(PASSWORD_COMMANDS)
    elif query.data == 'linux_commands':
        query.message.reply_text(LINUX_COMMANDS)
    elif query.data == 'db_commands':
        query.message.reply_text(DB_COMMANDS)
    elif query.data == 'all_packages':
        result = system('apt list --installed | tail -10')
        query.message.reply_text(f'Все пакеты:\n{result}')


def find_email(update: Update, context):
    update.message.reply_text('Введи текст, содержащий адреса почты:\n/cancel - отменить действие')
    return EMAIL_INPUT


def input_email(update: Update, context):
    r = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+')
    emails = set(re.findall(r, update.message.text))
    if emails:
        result = ''
        for email in emails:
            result += f"{email}\n"
        with open('buffer.txt','w') as file:
            file.write(result)
        result += '\n\n/write - записать данные в базу'
    else:
        result = 'К сожалению не смог найти email...'
    update.message.reply_text(result)
    return ConversationHandler.END


def find_phone(update: Update, context):
    update.message.reply_text('Введи текст, содержащий номера телефонов:\n/cancel - отменить действие')
    return PHONE_INPUT


def input_phone(update: Update, context):
    r = re.compile(r'(\+7|8)[ -.]?(\(\d{3}\)|\d{3})[ -.]?(\(\d{3}\)|\d{3})[ -.]?(\d{2})[ -.]?(\d{2})')
    phones = set(re.findall(r, update.message.text))
    if phones:
        result = ''
        for phone in phones:
            phone = f"{'-'.join(phone)}\n".replace('+7', '8').replace('.', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
            result += phone
        with open('buffer.txt', 'w') as file:
            file.write(result)
        result += '\n\n/write - записать данные в базу'
    else:
        result = 'К сожалению не смог найти номера телефонов...'
    update.message.reply_text(result)
    return ConversationHandler.END


def write(update: Update, context):
    with open('buffer.txt', 'r') as file:
        data = [f"('{d[:-1]}')" for d in file]
    if data[0].startswith("('8"):
        table = 'phones (phone)'
    else:
        table = 'emails (email)'
    command = f'insert into {table} values {",".join(data)}' + ';'
    db_execute(command, select=False)
    update.message.reply_text('Данные записаны!')



def verify_password(update: Update, context):
    update.message.reply_text('Введи пароль:\n/cancel - отменить действие')
    return PASSWORD_INPUT


def input_password(update: Update, context):
    password = update.message.text
    result = "Пароль достаточно безопасен!"
    if len(password) < 8:
        result = "Пароль слишком короткий! Минимум 8 символов."
    if not re.search("[a-z]", password):
        result = "Пароль должен содержать хотя бы одну строчную букву."
    if not re.search("[A-Z]", password):
        result = "Пароль должен содержать хотя бы одну заглавную букву."
    if not re.search("[0-9]", password):
        result = "Пароль должен содержать хотя бы одну цифру."
    if not re.search("[!@#$%^&*(),.?\":{}|<>]", password):
        result = "Пароль должен содержать хотя бы один специальный символ."
    update.message.reply_text(result)
    return ConversationHandler.END    


def get_release(update: Update, context):
    result = system('lsb_release -a')
    update.message.reply_text(f'Релиз:\n{result}')


def get_uname(update: Update, context):
    result = system('echo "Архитектура: $(uname -m)\nИмя хоста: $(hostname)\nВерсия ядра: $(uname -r)"')
    update.message.reply_text(result)


def get_uptime(update: Update, context):
    result = system('uptime -p')
    update.message.reply_text(f'Время работы:\n{result}')


def get_df(update: Update, context):
    result = system('df -h')
    update.message.reply_text(f'Состояние файловой системы:\n{result}')


def get_free(update: Update, context):
    result = system('free -h')
    update.message.reply_text(f'Состояние оперативной памяти:\n{result}')


def get_mpstat(update: Update, context):
    result = system('mpstat 1 5')
    update.message.reply_text(f'Производительность системы:\n{result}')


def get_w(update: Update, context):
    result = system('who')
    update.message.reply_text(f'Работающие пользователи:\n{result}')


def get_auths(update: Update, context):
    result = system('last -n 10')
    update.message.reply_text(f'Последние 10 входов в систему:\n{result}')


def get_critical(update: Update, context):
    result = system('journalctl -p crit -n 5')
    update.message.reply_text(f'Последние 5 критических событий:\n{result}')


def get_ps(update: Update, context):
    result = system('ps aux | tail -10')
    update.message.reply_text(f'Запущенные процессы:\n{result}')


def get_ss(update: Update, context):
    result = system('ss -tuln')
    update.message.reply_text(f'Используемые порты:\n{result}')


def get_apt_list(update: Update, context):
    result = system(f'apt list --installed | tail -10')
    update.message.reply_text(f'Информация об установленных пакетах:\n{result}')


def get_some_package(update: Update, context):
    update.message.reply_text('Введи название пакета:\n/cancel - отменить действие')
    return PACKAGE_INPUT


def get_repl_log(update: Update, context):
    logs = system(command=f'cd /var/log/postgresql && echo {RM_PASSWORD} | sudo -S cat $(ls -t /var/log/postgresql | head -n 1) | tail -5', host=os.getenv('DB_HOST'))
    update.message.reply_text(f'Логи о репликации:\n{logs}')
    if "LOG" not in logs:
        try:
            log_dir = "/var/log/postgresql/"
            log_files = glob.glob(os.path.join(log_dir, "*.log"))
            latest_log_file = max(log_files, key=os.path.getmtime)
            with open(latest_log_file, 'r') as log_file:
                logs = log_file.read()
        except Exception as e:
            logs = 'Ошибка'
        update.message.reply_text(f'Логи о репликации:\n{logs}')


def input_package(update: Update, context):
    package = update.message.text
    result = system(f'apt show {package}')
    update.message.reply_text(f'Информация о пакете {package}:\n{result}')
    return ConversationHandler.END


def get_emails(update: Update, context):
    objects = db_execute('select * from emails;')
    if objects:
        result = 'Email в базе:\n'
        for o in objects:
            result += f'{o}\n'
    else:
        result = 'Пока таблица с email-ами пустая...'
    update.message.reply_text(result)


def get_phones(update: Update, context):
    objects = db_execute('select * from phones;')
    if objects:
        result = 'Телефоны в базе:\n'
        for o in objects:
            result += f'{o}\n'
    else:
        result = 'Пока таблица с телефонами пустая...'
    update.message.reply_text(result)


def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher		
    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", start))
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(CommandHandler("get_apt_list", get_apt_list))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phones))
    dp.add_handler(CommandHandler("get_repl_log", get_repl_log))
    dp.add_handler(CommandHandler("write", write))

    # Регистрируем обработчик нажатия кнопок
    dp.add_handler(CallbackQueryHandler(button))
		
    # Используем ConversationHandler для управления многошаговыми процессами
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('find_email', find_email),
            CommandHandler('find_phone_number', find_phone),
            CommandHandler('verify_password', verify_password),
            CommandHandler('get_some_package', get_some_package),
        ],
        states={
            EMAIL_INPUT: [MessageHandler(Filters.text & ~Filters.command, input_email)],
            PHONE_INPUT: [MessageHandler(Filters.text & ~Filters.command, input_phone)],
            PASSWORD_INPUT: [MessageHandler(Filters.text & ~Filters.command, input_password)],
            PACKAGE_INPUT: [MessageHandler(Filters.text & ~Filters.command, input_package)],
        },
        fallbacks=[CommandHandler('cancel', start)]
    )
    dp.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
