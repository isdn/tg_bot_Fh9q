from dataclasses import dataclass, make_dataclass
from io import TextIOWrapper
from typing import Any
from threading import Event
from queue import Queue
from time import sleep
from datetime import datetime
from subprocess import run, TimeoutExpired, CalledProcessError
from logging import Logger
import builtins
import operator

from logger import get_logger


@dataclass
class BaseSensors:
    def set(self, field, val):
        setattr(self, field, val)

    def get(self, field):
        return getattr(self, field)


@dataclass
class Alert:
    time: str
    sensor: str
    message: str


def format_alert_message(sensor: str, trigger: str, text: str, current: Any) -> str:
    return "<b>" \
           f"{text.format(sensor=sensor, trigger=trigger, value=current)}" \
           "</b>"


def check_sensors(sensors: BaseSensors, alerts: Queue, cfg: dict[str, Any], logger: Logger) -> None:
    ops = {
        'ge': operator.ge,
        'le': operator.le,
        'gt': operator.gt,
        'lt': operator.lt,
        'eq': operator.eq,
        'ne': operator.ne
    }
    for sensor, params in cfg.items():
        if not type(params.get('trigger', '')) is dict:
            continue
        for op, val in params['trigger'].items():
            if sensors.get(sensor) \
                    and op in ops \
                    and ops.get(op)(sensors.get(sensor), val):
                logger.debug(f"check_sensors: {sensor} {op} {val} >>> {sensors}")
                alert = Alert(time=datetime.now().strftime("%H:%M:%S"),
                              sensor=sensor,
                              message=format_alert_message(sensor=sensor, trigger=f"{op} {val}",
                                                           text=params.get('alert_text', "{sensor}: {value} {trigger}"),
                                                           current=sensors.get(sensor)
                                                           )
                              )
                alerts.put(alert)
                logger.info(alert)
    return


def update_sensors(sensors: BaseSensors, state: Queue, cfg: dict[str, Any], logger: Logger) -> None:
    for sensor, params in cfg['sensors'].items():
        try:
            # result = run(shlex.split(params['cmd'])...
            result = run(params['cmd'], timeout=2, check=True, capture_output=True, text=True,
                         shell=cfg['app']['use_shell']).stdout.strip()
        except OSError | ValueError | TimeoutExpired | CalledProcessError | TextIOWrapper:
            logger.error(f"update_sensors: sensor {sensor} cmd exec error -> {params['cmd']}")
            return
        try:
            val = getattr(builtins, params['type'])(result) if len(result) > 0 else False
        except ValueError:
            val = False
        sensors.set(sensor, val)
    logger.debug(f"update_sensors: {sensors}")
    if not state.empty():
        state.get()
    state.put(sensors)


def update_sensors_thread(state: Queue, alerts: Queue, cfg: dict[str, Any], stop: Event) -> None:
    sensors_logger = get_logger(name='sensors', cfg=cfg['app'])
    sensors_logger.debug("Starting sensors thread.")
    sensors = init_sensors_object(cfg['sensors'])
    while not stop.is_set():
        try:
            update_sensors(sensors=sensors, state=state, cfg=cfg, logger=sensors_logger)
            if cfg['app']['enable_alerts']:
                check_sensors(sensors=sensors, alerts=alerts, cfg=cfg['sensors'], logger=sensors_logger)
            sleep(cfg['app'].get('sensors_refresh_time', 5))
        except KeyboardInterrupt:
            return


def init_sensors_object(cfg: dict[str, Any]) -> BaseSensors:
    sensors_fields = [
        (k, getattr(builtins, v['type']) | bool)
        for k, v in cfg.items()
        if v.get('type') in ['str', 'int', 'float']
    ]
    sensors = BaseSensors()
    sensors.__class__ = make_dataclass("Sensors", fields=sensors_fields, bases=(BaseSensors,))
    return sensors
