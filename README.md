This telegram bot is purposed to check various _sensors_ and alert on different conditions.
Requirements:
- Python 3.10+
- PyYAML
- Requests

This bot uses long polling mechanism to receive updates from telegram.

#### Sensors

A sensor is something that can produce value. For example:
```shell
# generate a pseudo-random number
echo "$((($(date +%s))%100))"
echo $((($$)%100))
# read CPU temperature
cat /sys/devices/platform/nct6775.656/hwmon/hwmon1/temp7_input
# read fan speed
cat /sys/devices/platform/nct6775.656/hwmon/hwmon1/fan1_input
```

Sensors are defined in config like the following:
```yaml
  test_int:
    type: int
    cmd: 'cat /sys/devices/platform/nct6775.656/hwmon/hwmon1/fan1_input'
  test_str:
    type: str
    cmd: 'cat /path/to/test_generator'
```
- `test_int` / `test_str` - sensor names
- `type` - type of produced value (`str`|`int`|`float`)
- `cmd` - command


#### Alerts

Alerts can be enabled via config:
```yaml
app:
  enable_alerts: yes
```
A value can be `true`|`on`|`enable`|`yes` to enable.  
Other values disable alerts.  
Also, it can be disabled via CLI parameters `-da` or `--disable-alerts` (overrides config).

An alert is triggered when a target sensor value meets a condition.  

For example:

```yaml
  range_int:
    type: int
    cmd: 'echo $((($$)%100))'
    alert_text: "The {sensor} value is out of range.\nCurrent value is {value}, which {trigger}."
    trigger:
      ge: 90
      le: 10
```
- `alert_text` - text of the alert
- `{sensor}`, `{value}` and `{trigger}` - placeholders for name, current value and condition

Trigger conditions:
- `ge`: greater or equal
- `le`: less or equal
- `gt`: greater than
- `lt`: less than
- `eq`: equal
- `ne`: not equal


#### Run a command

This bot also can run a command (function) on the server.  
Commands should be defined in the config (`<command>: <function>`) and described in the code.
For example:
```yaml
commands:
  status: get_status
```

```python
def get_status() -> str:
    return "<b>Status</b>: OK\n"

def get_status(state: Queue) -> str:
    return "<b>Status</b>: OK\n"
```
A current state of sensors is passed to all such functions.


#### Logging

A loglevel can be set up via config:
```yaml
app:
  log_level: debug
```
Allowed values are `debug`|`info`|`warning`|`error`.  
Default (if `log_level` was not set in config) is `warning`.  
Debug mode can be activated via CLI: `-d` or `--debug`.


#### CLI

```shell
usage: main.py [-h] [-c config.yaml] [-da] [-d]

options:
  -h, --help            show this help message and exit
  -c config.yaml, --config config.yaml
                        Config file in yaml format. If none specified, the default is config.yaml
  -da, --disable-alerts
                        Disable alerts. Overrides the config value.
  -d, --debug           Activate the debug loglevel. Overrides the config value.
```


#### Config

Here is a config example:
```yaml
bot:
  api_url: 'https://api.telegram.org/bot'
  token: 'your token'
  chat_id: 12345678
  allowed_users:
      - 12345678
app:
  log_level: debug
  sensors_refresh_time: 4
  enable_alerts: yes
  use_shell: on
sensors:
  gt_int:
    type: int
    cmd: 'echo "$((($(date +%s))%100))"'
    trigger:
      gt: 80
  range_int:
    type: int
    cmd: 'echo $((($$)%100))'
    alert_text: "The {sensor} value is out of range.\nCurrent value is {value}, which {trigger}."
    trigger:
      ge: 90
      le: 10
  eq_float:
    type: float
    cmd: 'cat /path/to/test_generator/test_float'
    trigger:
      eq: 55.0
  test_str:
    type: str
    cmd: 'cat /path/to/test_generator/test_str_1'
    trigger:
      ne: 'test_str'
  another_test_str:
    type: str
    cmd: 'cat /path/to/test_generator/test_str_2'
commands:
  status: get_status
  test: get_test
```

