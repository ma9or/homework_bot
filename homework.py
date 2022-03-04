import os
import logging
import telegram
import time
import requests
import json
import exceptions as ex

from http import HTTPStatus
from dotenv import load_dotenv
from telegram.error import TelegramError


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(level=logging.INFO,
                    filename='main.log',
                    filemode='a',
                    format='%(asctime)s, %(levelname)s, %(message)s')

logger = logging.getLogger(__name__)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено')
    except TelegramError(message):
        message = 'сообщение не отправлено'
        logger.error(message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)

    if response.status_code == HTTPStatus.OK:
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            logger.error('не json')
    else:
        message = 'нет ответа от эндпоинта'
        logger.error(message)
        raise ex.NegativeValueAPI(message)


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) is not dict:
        message = 'Ответ API не словарь'
        logger.error(message)
        raise TypeError(message)
    try:
        if len(response['homeworks']) == 0:
            raise ex.EmptyList('пустой список')

    except KeyError as error:
        message = f'ключ отсутствует: {error}'
        raise KeyError(message)

    if type(response['homeworks']) is not list:
        raise ex.NegativeValueException('домашки приходят не в виде списка')
    homework = response["homeworks"]
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной."""
    """домашней работе статус этой работы."""
    if 'homework_name' not in homework:
        logger.error('В ответе API не содержится ключ homework_name.')
        raise KeyError(
            'В ответе API не содержится ключ homework_name.'
        )

    if 'status' not in homework:
        logger.error('В ответе API не содержится ключ status.')
        raise KeyError('В ответе API не содержится ключ status.')

    if homework['status'] not in HOMEWORK_STATUSES:
        raise KeyError('ошибка статуса')

    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES[homework_status]

    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


def check_tokens():
    """Доступны переменные окружения."""
    token_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    if not all(token_list):
        message = 'Отсутствует или не задана переменная окружения.'
        logger.critical(message)
        return False
    return True


def main():
    """Основная логика работы бота."""
    check_result = check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    if not check_result:
        message = 'Аутентификация не удалась'
        logger.critical(message)
        raise SystemExit(message)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)[0]

            if homework is not None:
                message = parse_status(homework)
                if message is not None:
                    send_message(bot, message)

            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        else:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
