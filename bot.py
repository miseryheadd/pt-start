import logging
import os
from dotenv import load_dotenv
import re
import paramiko
import psycopg2
from psycopg2 import Error
from pathlib import Path
from telegram import Update
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

load_dotenv()
TOKEN = os.getenv('TOKEN')
rm_user = os.getenv('RM_USER')
rm_password = os.getenv('RM_PASSWORD')
rm_host = os.getenv('RM_HOST')
rm_port = os.getenv('RM_PORT')
username_db = os.getenv('DB_USER')
password_db = os.getenv('DB_PASSWORD')
host_db = os.getenv('DB_HOST')
database = os.getenv('DB_DATABASE')
port_db = os.getenv('DB_PORT')

logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)


def start(update: Update, context):
    user = update.effective_user
    update.message.reply_text(f'Привет, {user.full_name}! Введи /help для вывода списка доступных команд.')
    logger.info(f'Пользователь {user.full_name} запустил бота.')


def helpCommand(update: Update, context):
    logger.info('Пользователь запросил помощь.')
    update.message.reply_text(
        'Список доступных команд:\n'
        '/findPhoneNumbers - поиск телефонных номеров\n'
        '/findEmailAddresses - поиск email\n'
        '/verifyPassword - проверка сложности пароля\n'
        '/get_auths - последние 10 входов в систему\n'
        '/get_critical - последние 5 критических событий\n'
        '/get_ps - запущенные процессы\n'
        '/get_ss - используемые порты\n'
        '/get_apt_list - установленные пакеты\n'
        '/get_df - состояние файловой системы\n'
        '/get_free - состояние оперативной памяти\n'
        '/get_mpstat - производительность системы\n'
        '/get_w - работающие пользователи\n'
        '/get_release - информация о релизе\n'
        '/get_uname - информация об архитектуре процессора, имени хоста и версии ядра\n'
        '/get_uptime - время работы системы\n'
        '/get_services - запущенные сервисы\n'
        '/get_repl_logs - просмотр логов репликации\n'
        '/get_emails - посмотреть все почты в БД\n'
        '/get_phone_numbers - посмотреть все номера в БД\n'
    )


# Объявляем состояния разговора
CONFIRMATION, ADD_TO_DB = range(2)


def findPhoneNumbersCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')
    logger.info('Пользователь запросил поиск телефонных номеров.')
    return CONFIRMATION


# Обработчик состояния CONFIRMATION для phone
def confirmFoundNumbers(update: Update, context):
    user_input = update.message.text
    phoneNumRegex = re.compile(r'(?:\+7|8)[\- ]?\(?\d{3}\)?[\- ]?\d{3}[\- ]?\d{2}[\- ]?\d{2}')
    phoneNumberList = phoneNumRegex.findall(user_input)
    standardizedPhoneNumbers = []
    for phone_number in phoneNumberList:
        standardized_number = re.sub(r'\D', '', phone_number)
        standardized_number = '8' + standardized_number[1:]
        standardizedPhoneNumbers.append(standardized_number)

    if not phoneNumberList:
        update.message.reply_text('Телефонные номера не найдены')
        return ConversationHandler.END

    # Предложение добавить номера в базу данных
    reply_keyboard = [['Да', 'Нет']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text(
        'Найдены следующие номера:\n\n' + '\n'.join(standardizedPhoneNumbers) +
        '\n\nХотите добавить их в базу данных?', reply_markup=markup
    )
    context.user_data['phone_numbers'] = standardizedPhoneNumbers
    context.user_data['data_type'] = 'phone_numbers'
    return ADD_TO_DB


def findEmailAddressesCommand(update: Update, context):
    update.message.reply_text('Введите текст для поиска email-адресов: ')
    logger.info('Пользователь запросил поиск email-адресов.')
    return CONFIRMATION


def confirmEmails(update: Update, context):
    user_input = update.message.text
    emailRegex = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    emailAddressesList = emailRegex.findall(user_input)

    if not emailAddressesList:
        update.message.reply_text('Email-адреса не найдены')
        return ConversationHandler.END

    # Предложение добавить номера в базу данных
    reply_keyboard = [['Да', 'Нет']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text(
        'Найдены следующие номера:\n\n' + '\n'.join(emailAddressesList) +
        '\n\nХотите добавить их в базу данных?', reply_markup=markup
    )
    context.user_data['data_type'] = 'email_addresses'
    context.user_data['email_addresses'] = emailAddressesList

    return ADD_TO_DB


def verifyPasswordCommand(update: Update, context):
    update.message.reply_text('Введите пароль для проверки: ')
    return 'verifyPassword'


def verifyPassword(update: Update, context):
    user_input = update.message.text
    if re.match(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()]).{8,}$', user_input):
        update.message.reply_text('Пароль сложный')
        return ConversationHandler.END
    else:
        update.message.reply_text('Пароль простой')
        return ConversationHandler.END


# Функция для подключения к базе данных
def connect_to_db():
    try:
        connection = psycopg2.connect(
            user=username_db,
            password=password_db,
            host=host_db,
            port=port_db,
            database=database
        )
        return connection
    except (Exception, psycopg2.Error) as error:
        logger.error("Ошибка при работе с PostgreSQL: %s", error)
        return None


# Обработчик состояния ADD_TO_DB
def addToDB(update: Update, context):
    user_input = update.message.text
    data_type = context.user_data.get('data_type')

    if user_input == 'Да':
        if data_type == 'phone_numbers':
            phone_numbers = context.user_data.get('phone_numbers')
            add_phone_numbers_to_db(phone_numbers)
            update.message.reply_text('Номера успешно добавлены в базу данных')
        elif data_type == 'email_addresses':
            email_addresses = context.user_data.get('email_addresses')
            add_email_addresses_to_db(email_addresses)
            update.message.reply_text('Email-адреса успешно добавлены в базу данных')
    else:
        update.message.reply_text('Ок, данные не добавлены в базу данных')

    return ConversationHandler.END


# Функция для добавления почт в базу данных
def add_email_addresses_to_db(email_addresses):
    connection = connect_to_db()
    if connection is None:
        return

    try:
        cursor = connection.cursor()
        for email_address in email_addresses:
            cursor.execute("INSERT INTO email (email_address) VALUES (%s)", (email_address,))
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        logger.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()


# Функция для добавления номеров в базу данных
def add_phone_numbers_to_db(phone_numbers):
    connection = connect_to_db()
    if connection is None:
        return

    try:
        cursor = connection.cursor()
        for phone_number in phone_numbers:
            cursor.execute("INSERT INTO phone (phone_number) VALUES (%s)", (phone_number,))
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        logger.error("Ошибка при работе с PostgreSQL: %s", error)
    finally:
        if connection is not None:
            cursor.close()
            connection.close()


# Функция для установления SSH-подключения
def ssh_connect():
    host = rm_host
    port = int(rm_port)
    username = rm_user
    password = rm_password
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, username, password)

    return ssh


# Функция для установления SSH-подключения к бд
def ssh_connect_db():
    host = host_db
    port = int(rm_port)
    username = username_db
    password = password_db
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port, username, password)

    return ssh


# Функция для выполнения команды по SSH
def execute_ssh_command(ssh, command):
    # Выполняем команду на удаленном сервере
    stdin, stdout, stderr = ssh.exec_command(command)
    # Читаем результат выполнения команды
    output = stdout.read().decode('utf-8')
    # Закрываем соединение
    ssh.close()

    return output


# Функция для получения информации о релизе
def get_release():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'cat /etc/*release')
    return output


# Функция для получения информации об архитектуре процессора, имени хоста системы и версии ядра
def get_uname():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'uname -a')
    return output


# Функция для получения информации о времени работы
def get_uptime():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'uptime')
    return output


# Функция для получения информации о состоянии файловой системы
def get_df():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'df -h')
    return output


# Функция для получения информации о состоянии оперативной памяти
def get_free():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'free -h')
    return output


# Функция для получения информации о производительности системы
def get_mpstat():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'mpstat')
    return output


# Функция для получения информации о работающих в данной системе пользователях
def get_w():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'w')
    return output


# Функция для получения последних 10 входов в систему
def get_auths():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'tail -n 10 /var/log/auth.log')
    return output


# Функция для получения последних 5 критических событий
def get_critical():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'tail -n 5 /var/log/syslog | grep -i "critical"')
    return output


# Функция для получения информации о запущенных процессах
def get_ps():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'ps aux | head -n 10')
    return output


# Функция для получения информации об используемых портах
def get_ss():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'ss -tuln')
    return output


# Функиця для получения информации об установленных пакетах
def get_apt_list(update: Update, context):
    user_input = update.message.text
    ssh = ssh_connect()
    if user_input == 'all':
        output = execute_ssh_command(ssh, 'dpkg-query -l | tail -n 13')
        update.message.reply_text(output)
        return ConversationHandler.END
    else:
        package_name = user_input.strip()
        try:
            output = execute_ssh_command(ssh, f'dpkg-query -s {package_name}')
            update.message.reply_text(output)
        except:
            output = f"Пакет '{package_name}' не найден."
            update.message.reply_text(output)
        return ConversationHandler.END


# Функция для получения информации о запущенных сервисах
def get_services():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'systemctl list-units --type=service | head -n 10')
    return output


# Функция для получения логов бд
def get_repl_logs():
    ssh = ssh_connect()
    output = execute_ssh_command(ssh, 'cat /var/log/postgresql/postgresql-14-main.log | tail -n 6')
    return output


# Функция для получения номеров из бд
def get_phone_numbers():
    connection = connect_to_db()
    if connection is None:
        return
    try:
        cursor = connection.cursor()

        # Выполнение запроса к базе данных для получения email-адресов
        cursor.execute("SELECT phone_number FROM phone;")
        phone_numbers = cursor.fetchall()

        # Формирование текстового сообщения с номерами телефонов
        phone_numbers_message = "\n".join([phone[0] for phone in phone_numbers])
        output = ("Номера телефонов:\n" + phone_numbers_message)

    except (Exception, psycopg2.Error) as error:
        output = f"Ошибка при работе с PostgreSQL: {error}"
        logger.error("Ошибка при работе с PostgreSQL: %s", error)

    finally:
        # Закрытие соединения с базой данных
        if connection is not None:
            cursor.close()
            connection.close()
            return output


# Функция для получения почт из бд
def get_emails():
    connection = connect_to_db()
    if connection is None:
        return
    try:
        cursor = connection.cursor()

        # Выполнение запроса к базе данных для получения email-адресов
        cursor.execute("SELECT email_address FROM email;")
        emails = cursor.fetchall()

        # Формирование текстового сообщения с email-адресами
        email_message = "\n".join([email[0] for email in emails])
        output = ("Email-адреса:\n" + email_message)

    except (Exception, psycopg2.Error) as error:
        output = f"Ошибка при работе с PostgreSQL: {error}"
        logger.error("Ошибка при работе с PostgreSQL: %s", error)

    finally:
        # Закрытие соединения с базой данных
        if connection is not None:
            cursor.close()
            connection.close()
            return output


# Функция обработки команды /get_release
def get_release_command(update: Update, context):
    update.message.reply_text(get_release())


# Функция обработки команды /get_uname
def get_uname_command(update: Update, context):
    update.message.reply_text(get_uname())


# Функция обработки команды /get_uptime
def get_uptime_command(update: Update, context):
    update.message.reply_text(get_uptime())


# Функция обработки команды /get_df
def get_df_command(update: Update, context):
    update.message.reply_text(get_df())


# Функция обработки команды /get_free
def get_free_command(update: Update, context):
    update.message.reply_text(get_free())


# Функция обработки команды /get_mpstat
def get_mpstat_command(update: Update, context):
    update.message.reply_text(get_mpstat())


# Функция обработки команды /get_w
def get_w_command(update: Update, context):
    update.message.reply_text(get_w())


# Функция обработки команды /get_auths
def get_auths_command(update: Update, context):
    update.message.reply_text(get_auths())


# Функция обработки команды /get_critical
def get_critical_command(update: Update, context):
    update.message.reply_text(get_critical())


# Функция обработки команды /get_ps
def get_ps_command(update: Update, context):
    update.message.reply_text(get_ps())


# Функция обработки команды /get_ss
def get_ss_command(update: Update, context):
    update.message.reply_text(get_ss())


# Функция для обработки команды /get_apt_list
def get_apt_list_command(update: Update, context):
    update.message.reply_text(
        'Введите all для вывода всех пакетов\nЕсли нужно найти конкретный пакет, введите его название ')
    return 'get_apt_list'


# Функция обработки команды /get_services
def get_services_command(update: Update, context):
    update.message.reply_text(get_services())


# Функция обработки команды /get_repl_logs
def get_repl_logs_command(update: Update, context):
    update.message.reply_text(get_repl_logs())


# Функция обработки команды /get_emails
def get_emails_command(update: Update, context):
    emails_text = get_emails()
    if emails_text:
        update.message.reply_text(emails_text)
    else:
        update.message.reply_text("Нет данных об email-адресах.")


# Функция обработки команды /get_phone_numbers
def get_phone_numbers_command(update: Update, context):
    update.message.reply_text(get_phone_numbers())


def echo(update: Update, context):
    update.message.reply_text(update.message.text)


def main():
    updater = Updater(TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # обработчик номеров
    convHandlerFindPhoneNumbers = ConversationHandler(
        entry_points=[CommandHandler('findPhoneNumbers', findPhoneNumbersCommand)],
        states={
            CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmFoundNumbers)],
            ADD_TO_DB: [MessageHandler(Filters.text & ~Filters.command, addToDB)],
        },
        fallbacks=[]
    )

    # обработчик почты
    convHandlerFindEmailAddresses = ConversationHandler(
        entry_points=[CommandHandler('findEmailAddresses', findEmailAddressesCommand)],
        states={
            CONFIRMATION: [MessageHandler(Filters.text & ~Filters.command, confirmEmails)],
            ADD_TO_DB: [MessageHandler(Filters.text & ~Filters.command, addToDB)],
        },
        fallbacks=[]
    )

    # обработчик пароля
    convHandlerVerifyPassword = ConversationHandler(
        entry_points=[CommandHandler('verifyPassword', verifyPasswordCommand)],
        states={
            'verifyPassword': [MessageHandler(Filters.text & ~Filters.command, verifyPassword)]
        },
        fallbacks=[]
    )

    convHandlerGetAptLists = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list_command)],
        states={'get_apt_list': [MessageHandler(Filters.text & ~Filters.command, get_apt_list)]},
        fallbacks=[]
    )

    # Регистрируем обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", helpCommand))
    dp.add_handler(convHandlerFindPhoneNumbers)
    dp.add_handler(convHandlerFindEmailAddresses)
    dp.add_handler(convHandlerVerifyPassword)
    dp.add_handler(convHandlerGetAptLists)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    dp.add_handler(CommandHandler("get_release", get_release_command))
    dp.add_handler(CommandHandler("get_uname", get_uname_command))
    dp.add_handler(CommandHandler("get_uptime", get_uptime_command))
    dp.add_handler(CommandHandler("get_df", get_df_command))
    dp.add_handler(CommandHandler("get_free", get_free_command))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat_command))
    dp.add_handler(CommandHandler("get_w", get_w_command))
    dp.add_handler(CommandHandler("get_auths", get_auths_command))
    dp.add_handler(CommandHandler("get_critical", get_critical_command))
    dp.add_handler(CommandHandler("get_ps", get_ps_command))
    dp.add_handler(CommandHandler("get_ss", get_ss_command))
    dp.add_handler(CommandHandler("get_services", get_services_command))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs_command))
    dp.add_handler(CommandHandler("get_emails", get_emails_command))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers_command))
    # Запускаем бота
    updater.start_polling()
    # Останавливаем бота при нажатии Ctrl+C
    updater.idle()


if __name__ == '__main__':
    main()
