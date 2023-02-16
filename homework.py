import logging
import os
import sys
import time
from http import HTTPStatus
from http.client import responses

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

formatter = logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
    filename="main.log",
    filemode="w",
)

RETRY_PERIOD = 600
FIRST_OBJECT = 0
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens():
    """Checking the availability of all tokens."""
    list_of_tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    flag = True
    for token in list_of_tokens:
        if not token:
            logging.critical(
                f"Necessary variables are missing. "
                f"Check all variables in list_of_tokens."
            )
            flag = False
            break
    return flag


def get_api_answer(timestamp):
    """Request to the API service endpoint."""
    try:
        PAYLOAD = {"from_date": timestamp}
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=PAYLOAD
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            logging.error(
                f"Server answer - code: {homework_statuses.status_code}, "
                f"name: {responses[homework_statuses.status_code]}"
            )
            raise requests.RequestException(
                f"Some problems with server. "
                f"Code: {homework_statuses.status_code}"
            )
        return homework_statuses.json()
    except requests.RequestException:
        logging.error(
            f"Server answer - code: {homework_statuses.status_code}, "
            f"name: {responses[homework_statuses.status_code]}"
        )
        raise requests.RequestException(
            f"Some problems with server. Code: {homework_statuses.status_code}"
        )


def check_response(response):
    """Checking API response for compliance with the documentation."""
    if not isinstance(response, dict):
        raise TypeError("Object 'homework' must be dict.")

    if not response.get("homeworks"):
        logging.error(f"Key access error 'homeworks'.")
        raise KeyError(f"Key access error 'homeworks'.")
    else:
        homework = response.get("homeworks")
    if not isinstance(homework, list):
        raise TypeError("Object 'homework' must be list.")
    return homework


def parse_status(homework):
    """Getting status of homework."""
    if not homework.get("homework_name"):
        logging.error(f"Key access error 'homework_name'")
        raise KeyError(f"Key access error 'homework_name'")
    elif not homework.get("status"):
        logging.error(f"Key access error 'status'")
        raise KeyError(f"Key access error 'status'")
    else:
        homework_name = homework.get("homework_name")
        homework_status = homework.get("status")

    if not None and homework_status not in HOMEWORK_VERDICTS:
        logging.error(f"Unknown status: {homework_status}")
        raise KeyError(f"Unknown status: {homework_status}")
    else:
        verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Sending message to Telegram chat."""
    try:
        logging.debug(f'Bot Tries to send message: "{message}"')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f"The message has been sent")
    except Exception as error:
        logging.error(f"Sending message error: {error}")
        raise Exception(f"Sending message error: {error}")


def main():
    """Main bot's working logic."""
    if check_tokens():
        logging.info("All tokens are available.")
    else:
        sys.exit()
    last_status = ""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - RETRY_PERIOD
    while True:
        try:
            result = get_api_answer(timestamp)
            if check_response(result)[FIRST_OBJECT]:
                if len(check_response(result)[FIRST_OBJECT]) > 0:
                    homework = check_response(result)[FIRST_OBJECT]
                    current_status = homework.get("status")
                    if current_status != last_status:
                        message = parse_status(homework)
                        send_message(bot, message)
                        last_status = message
            else:
                logging.debug("No updates.")
        except Exception as error:
            message = f"Program malfunction: {error}."
            logging.error(message)
        timestamp = int(time.time())
        time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
