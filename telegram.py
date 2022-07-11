from json import JSONDecodeError
from requests import post
from time import sleep
from threading import Event
from queue import Queue
from typing import Any
from logging import Logger

from logger import get_logger


def send_alerts_thread(alerts: Queue, cfg: dict[str, Any], stop: Event) -> None:
    alerts_logger = get_logger(name='alerts', cfg=cfg['app'])
    alerts_logger.debug("Starting alerts thread.")
    while not stop.is_set():
        try:
            alert = alerts.get()
            alerts_logger.debug(f"Alert: {alert}")
            send_message(msg=f"{alert.time}: {alert.sensor}\n{alert.message}", cfg=cfg['bot'], logger=alerts_logger)
        except KeyboardInterrupt:
            return


def get_updates_thread(cfg: dict[str, Any], state: Queue, stop: Event, offset=0) -> None:
    tg_logger = get_logger(name='tg', cfg=cfg['app'])
    tg_logger.debug("Starting updates thread.")
    wait_time = 60
    url = cfg['bot']['api_url'] + cfg['bot']['token'] + '/getUpdates'
    while not stop.is_set():
        data = {'offset': offset, 'timeout': wait_time}
        headers = {'Prefer': f'wait={wait_time}'}
        try:
            response = post(url=url, data=data, headers=headers, timeout=None)
        except KeyboardInterrupt:
            return
        except ValueError:
            continue
        code = response.status_code
        match code:
            case 401:
                tg_logger.critical("get_updates_thread: token is invalid.")
                stop.set()
                return
            case code if code >= 500:
                tg_logger.warning(f"get_updates_thread: response code {code}.")
                sleep(10)
                continue
            case code if code != 200:
                tg_logger.error(f"get_updates_thread: response error.\nCode: {str(code)}\nMessage: {response.text}")
                sleep(20)
                continue
        try:
            r = response.json()
            tg_logger.debug(f"get_updates_thread: response: {r}")
            if r.get('ok') is None or r.get('result') is None:
                continue
            for message in r['result']:
                offset = message['update_id'] + 1
                process_message(msg=message, state=state, cfg=cfg, logger=tg_logger)
        except JSONDecodeError as ex:
            tg_logger.error(f"get_updates_thread: JSON decode error: {ex.msg}")


def send_message(msg: str, cfg: dict[str, Any], logger: Logger) -> None:
    url = cfg['api_url'] + cfg['token'] + '/sendMessage'
    data = {'chat_id': cfg['chat_id'], 'parse_mode': 'HTML', 'text': msg}
    try:
        response = post(url=url, data=data, timeout=10)
    except ValueError:
        logger.error("send_message: request error.")
        return
    code = response.status_code
    if code != 200:
        logger.error(f"send_message: response error.\nCode: {str(code)}\nMessage: {response.text}")
        return
    try:
        r = response.json()
        logger.debug(f"send_message: response: {str(r)}")
        if r.get('ok') is None or r.get('result') is None:
            logger.error(f"send_message: response error: {str(r)}")
            return
    except JSONDecodeError as ex:
        logger.error(f"send_message: JSON decode error: {ex.msg}")


def process_message(msg: dict[str, Any], state: Queue, cfg: dict[str, Any], logger: Logger) -> None:
    if 'message' in msg and (text := msg['message'].get('text')) is not None:
        if type(cfg.get('commands', '')) is dict and is_allowed(msg['message'], cfg['bot']):
            if text in cfg['commands'] and cfg['commands'][text] in globals():
                result = globals()[cfg['commands'][text]](state)
                send_message(msg=result, cfg=cfg['bot'], logger=logger)
    else:
        return


def is_allowed(message: dict[str, Any], cfg: dict[str, Any]) -> bool:
    if 'from' in message and message['from']['id'] in cfg['allowed_users']:
        return True
    if 'chat' in message and message['chat']['id'] == cfg['chat_id']:
        return True
    return False


def get_status(state: Queue) -> str:
    sensors = state.get()
    message = ["<b>Status</b>:\n"]
    error_msg = "<b>Error</b>"
    for sensor, value in sensors.__dict__.items():
        message.append(f"{sensor}: {value if value else error_msg}\n")
    return "".join(message)
