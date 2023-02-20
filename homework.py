import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from OwnExceptions import TelegramError

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


def check_tokens() -> bool:
    """Checking the availability of all tokens."""
    if all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return True
    else:
        logging.critical(
            "Necessary variables are missing."
            "Check all variables in list_of_tokens."
        )
        return False


def get_api_answer(timestamp: int) -> dict:
    """Request to the API service endpoint."""
    try:
        logging.info("Starting API request with ENDPOINT, headers and params.")
        PAYLOAD = {"from_date": timestamp}
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=PAYLOAD
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            raise requests.RequestException(
                "Some problems with server."
                "Code: %s" % homework_statuses.status_code
            )
        return homework_statuses.json()
    except requests.RequestException:
        raise requests.RequestException(
            "Some problems with server. Code: %s"
            % homework_statuses.status_code
        )


def check_response(response: dict) -> list:
    """Checking API response for compliance with the documentation."""
    if not isinstance(response, dict):
        raise TypeError("Object 'homework' must be dict.")
    homework = response.get("homeworks")
    if homework is None:
        raise KeyError("Key access error 'homeworks'.")
    if not isinstance(homework, list):
        raise TypeError("Object 'homework' must be list.")
    return homework


def parse_status(homework: dict) -> str:
    """Getting status of homework."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")

    if homework_name is None:
        raise KeyError("Key access error 'homework_name'")
    elif homework_status is None:
        raise KeyError("Key access error 'status'")

    if (
        homework_status is not None
        and homework_status not in HOMEWORK_VERDICTS
    ):
        raise KeyError("Unknown status: %s" % homework_status)
    else:
        verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot: telegram.bot.Bot, message: str) -> str:
    """Sending message to Telegram chat."""
    try:
        logging.debug('Bot Tries to send message: "%s"' % message)
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug("The message has been sent")
    except telegram.error.TelegramError:
        logging.error("Mistake to send message")
        raise TelegramError(message)
    else:
        logging.info("Sending message: %s" % message)


def main() -> str:
    """Main bot's working logic."""
    if check_tokens():
        logging.info("All tokens are available.")
    else:
        sys.exit()
    last_status = ""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            result = get_api_answer(timestamp)
            homework = check_response(result)
            if len(homework) == 0:
                message = "К сожалению, обновлений нет."
                current_status = "no updates"
            else:
                current_status = homework[FIRST_OBJECT].get("status")
                message = parse_status(homework[FIRST_OBJECT])
            if current_status != last_status:
                last_status = message
                send_message(bot, message)
            else:
                logging.debug("No updates.")
        except Exception as error:
            message = f"Program malfunction: {error}."
            logging.error(message)
            send_message(bot, message)
        finally:
            timestamp = result.get("current_date")
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
