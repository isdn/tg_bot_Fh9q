from yaml import safe_load, YAMLError
from pathlib import Path
from sys import exit
from threading import Thread
from sys import stderr
from threading import Event
from time import sleep
from queue import Queue
from typing import Any
from argparse import ArgumentParser

from logger import get_logger
from telegram import get_updates_thread, send_alerts_thread
from sensors import update_sensors_thread


def read_config(file_name: str) -> dict[str, Any]:
    if Path(file_name).is_file():
        try:
            with open(file_name, 'r') as f:
                return safe_load(f)
        except OSError as ex:
            print(f"Cannot read config file: {ex.filename}\n{ex.strerror}", file=stderr)
            exit(1)
        except YAMLError as ex:
            if hasattr(ex, 'problem_mark'):
                err = ex.problem_mark
                print(f"Error in config file: line {err.line + 1}, column {err.column + 1}", file=stderr)
            else:
                print(f"Error in config file: {file_name}", file=stderr)
            exit(1)
    else:
        print(f"Config file not found: {file_name}", file=stderr)
        exit(1)


def check_config(cfg: dict[str, Any]) -> dict[str, Any] | bool:
    default_config = {
        'bot': dict,
        'app': dict,
        'sensors': dict,
        'commands': dict
    }
    bot_config = {
        'api_url': str,
        'token': str,
        'chat_id': int,
        'allowed_users': list
    }
    if not (all(key in cfg for key in default_config) and all(key in cfg['bot'] for key in bot_config)):
        return False
    if not (all(type(cfg[key]) is default_config[key] for key in default_config) and
            all(type(cfg['bot'][key]) is bot_config[key] for key in bot_config)):
        return False
    if not (all(type(cfg['sensors'][key]) is dict for key in cfg['sensors']) and len(cfg['sensors']) > 0):
        return False
    return cfg


def is_enabled(val: bool | str | None) -> bool:
    match val:
        case None | False:
            return False
        case True:
            return True
        case val:
            return val.lower() in ['true', 'on', 'enable', 'yes']


if __name__ == '__main__':
    parser = ArgumentParser(description="")
    parser.add_argument('-c', '--config', metavar='config.yaml', dest='config_file', default='config.yaml',
                        help="Config file in yaml format. If none specified, the default is config.yaml")
    parser.add_argument('-da', '--disable-alerts', dest='disable_alerts', action='store_true',
                        help="Disable alerts. Overrides the config value.")
    parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                        help="Activate the debug loglevel. Overrides the config value.")
    args = parser.parse_args()

    config = read_config(args.config_file)
    config = check_config(config)
    if not config:
        print(f"Config file is not valid: {args.config_file}", file=stderr)
        exit(1)
    if args.debug:
        config['app']['log_level'] = 'debug'
    config['app']['enable_alerts'] = not args.disable_alerts and is_enabled(config['app'].get('enable_alerts'))
    config['app']['use_shell'] = is_enabled(config['app'].get('use_shell'))

    main_logger = get_logger(name='main', cfg=config['app'])
    main_logger.info("Starting")
    main_logger.debug(f"Config: {config}")

    stop_event = Event()
    current_state = Queue(maxsize=1)
    alerts_queue = Queue(maxsize=1024)
    updates_thread = Thread(name='updates_thread', daemon=True, target=get_updates_thread,
                            args=(config, current_state, stop_event))
    sensors_thread = Thread(name='sensors_thread', daemon=True, target=update_sensors_thread,
                            args=(current_state, alerts_queue, config, stop_event))
    alerts_thread = Thread(name='alerts_thread', daemon=True, target=send_alerts_thread,
                           args=(alerts_queue, config, stop_event)) if config['app']['enable_alerts'] else None
    try:
        updates_thread.start()
        sensors_thread.start()
        if config['app']['enable_alerts']:
            alerts_thread.start()
        main_logger.info("Running")
        while True:
            if stop_event.is_set():
                raise KeyboardInterrupt
            sleep(60)
    except KeyboardInterrupt as e:
        stop_event.set()
        if updates_thread.is_alive():
            updates_thread.join(1)
        if sensors_thread.is_alive():
            sensors_thread.join(1)
        if config['app']['enable_alerts'] and alerts_thread.is_alive():
            alerts_thread.join(1)
    main_logger.info("Stopping")
    exit(0)
