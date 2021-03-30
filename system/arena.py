"""
Arena hardware controller
Author: Tal Eisenberg, 2021

This module provides convenience functions for communicating with the arena hardware
over MQTT. It allows sending commands, and also stores sensor readings in the global state.
"""

import mqtt
from state import state
import time

_sensors_once_callback = None
_log = None


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


def init(logger, arena_defaults):
    """
    Initialize the arena module.
    Connects to MQTT, sends arena defaults, and subscribes for sensor updates.

    - arena_defaults: A dict with signal_led and day_lights keys with default values.
    """
    global _log
    _log = logger

    state["arena"] = {"sensors": None}

    while not mqtt.client.is_connected:
        time.sleep(0.01)

    _log.info("Sending arena defaults.")
    signal_led(arena_defaults["signal_led"])
    day_lights(arena_defaults["day_lights"])

    mqtt.client.subscribe_callback(
        "arena/sensors", mqtt.mqtt_json_callback(_on_sensors)
    )
