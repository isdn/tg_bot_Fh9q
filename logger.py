import logging
from sys import stdout
from typing import Any


def get_logger(name: str, cfg: dict[str, Any]) -> logging.Logger:
    log_levels = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR
    }
    log_level = log_levels.get(cfg['log_level'].lower(), logging.WARNING) if cfg.get('log_level') is not None \
        else logging.WARNING
    lg = logging.getLogger(name)
    lg.setLevel(log_level)
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    handler.setStream(stdout)
    lg.addHandler(handler)
    return lg
