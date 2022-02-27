import os
import logging
import telegram
import time
import requests

from http import HTTPStatus
from dotenv import load_dotenv


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


class NegativeValueException(Exception):
    """Класс исключений."""

    pass


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Сообщение отправлено')
    except Exception as error:
        logging.error(error)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        message = 'API ведет себя незапланированно'
        logging.error(message)
        raise NegativeValueException(message)
    try:
        if response.status_code != HTTPStatus.OK:
            message = 'Сервер не отвечает'
            logging.error(message)
            raise Exception(message)
    except Exception:
        message = 'API ведет себя незапланированно'
        logging.error(message)
        raise NegativeValueException(message)
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if type(response) is not dict:
        message = 'Ответ API не словарь'
        logging.error(message)
        raise TypeError(message)
    elif ['homeworks'][0] not in response:
        message = 'В ответе API нет домашней работы'
        logging.error(message)
        raise IndexError(message)
    elif len(response['homeworks']) == 0:
        raise NegativeValueException('список пуст')
    elif type(response['homeworks']) is not list:
        raise NegativeValueException('домашки приходят не в виде списка')
    homework = response["homeworks"]

    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной."""
    """домашней работе статус этой работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_STATUSES:
        logging.debug('отсуствует в ответе новые статусы')
        raise NegativeValueException(
            "Cтатус отсутствующий в списке!"
        )

    verdict = HOMEWORK_STATUSES[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Доступны переменные окружения."""
    token_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        PRACTICUM_TOKEN,
    ]
    if not all(token_list):
        message = 'Отсутствует или не задана переменная окружения.'
        logging.critical(message)
        return False
    return True


def main():
    """Основная логика работы бота."""
    check_result = check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    if check_result is False:
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
