"""
Arena hardware controller
Author: Tal Eisenberg, 2021

This module provides convenience functions for communicating with the arena hardware
over MQTT. It allows sending commands, and also stores sensor readings in the global state.
"""

import mqtt
from state import state
import time
from subprocess import Popen, PIPE
import data_log

_sensors_once_callback = None
_log = None


def run_command(cmd):
    """Execute shell command"""
    process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        _log.info(f'Error running cmd: "{cmd}"; {stderr}')
    return stdout.decode("ascii")


def turn_touchscreen(on):
    DISPLAY_CMD = "DISPLAY=:0 xrandr --output HDMI-0 --{}"
    state["arena", "touchscreen"] = on

    if on:
        run_command(DISPLAY_CMD.format("auto"))
    else:
        run_command(DISPLAY_CMD.format("off"))


def dispense_reward():
    mqtt.client.publish("arena/dispense_reward")


def signal_led(on):
    mqtt.client.publish_json("arena/signal_led", on)
    state["arena", "signal_led"] = on


def day_lights(on):
    mqtt.client.publish_json("arena/day_lights", on)
    state["arena", "day_lights"] = on


def line(idx, on):
    """Set output digital line <idx> to state <on>"""
    mqtt.client.publish_json(f"arena/line/{idx}", on)


def start_trigger(pulse_len=None, update_state=True):
    if pulse_len is None:
        pulse_len = _config.video_record["trigger_interval"]

    if update_state:
        state["video", "record", "ttl_trigger"] = True
    mqtt.client.publish_json("arena/ttl_trigger/start", {"pulse_len": str(pulse_len)})


def stop_trigger(update_state=True):
    if update_state:
        state["video", "record", "ttl_trigger"] = False
    mqtt.client.publish("arena/ttl_trigger/stop")


def sensors_poll(callback_once=None):
    """
    Polls the sensors for new readings.
    - callback_once: A function with a single argument that will be called once
                     the sensor reading arrives.
    """
    global _sensors_once_callback

    _sensors_once_callback = callback_once
    mqtt.client.publish("arena/sensors/poll")


def sensors_set_interval(seconds):
    """Sets the amount of time between sensor readings in seconds"""
    mqtt.client.publish("arena/sensors/set_interval", seconds)


def _on_sensors(_, reading):
    global _sensors_once_callback

    reading["timestamp"] = time.time()

    state["arena", "sensors"] = reading
    if _sensors_once_callback is not None:
        _sensors_once_callback(reading)
        _sensors_once_callback = None

    # NOTE: This line depends on specific arena sensors reading format
    if "temp" not in reading:
        return

    _sensor_log.log(
        (
            reading["timestamp"],
            reading["temp"][0],
            reading["temp"][1],
            reading["temp"][2],
            reading["humidity"],
        )
    )


def init(logger, config):
    """
    Initialize the arena module.
    Connects to MQTT, inits sensor data logger, sends arena defaults, and subscribes for
    sensor updates.

    - arena_defaults: A dict with signal_led and day_lights keys with default values.
    """
    global _log, _sensor_log, _config
    _log = logger
    _config = config

    # NOTE: This data logger is specific to arena sensor reading format.
    _sensor_log = data_log.QueuedDataLogger(
        table_name="sensors",
        log_to_db=True,
        columns=(
            ("time", "timestamptz not null"),
            ("temp0", "double precision"),
            ("temp1", "double precision"),
            ("temp2", "double precision"),
            ("humidity", "double precision"),
        ),
    )
    _sensor_log.start()

    state["arena"] = {"sensors": None}

    while not mqtt.client.is_connected:
        time.sleep(0.01)

    _log.info("Sending arena defaults.")
    
    signal_led(config.arena_defaults["signal_led"])
    day_lights(config.arena_defaults["day_lights"])
    turn_touchscreen(config.arena_defaults["touchscreen"])

    mqtt.client.subscribe_callback(
        "arena/sensors", mqtt.mqtt_json_callback(_on_sensors)
    )


def release():
    mqtt.client.unsubscribe_callback("arena/sensors")
    _sensor_log.stop()
    _sensor_log.join()
