import mqtt
from state import state
import time
import config

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
    mqtt.client.publish_json(f"arena/line/{idx}", on)


def sensors_poll(callback_once):
    global _sensors_once_callback

    _sensors_once_callback = callback_once
    mqtt.client.publish("arena/sensors/poll")


def sensors_set_interval(seconds):
    # not implemented i think
    mqtt.client.publish("arena/sensors/set_interval", seconds)


def _on_sensors(_, reading):
    global _sensors_once_callback

    reading["timestamp"] = time.time()

    state["arena", "sensors"] = reading
    if _sensors_once_callback is not None:
        _sensors_once_callback(reading)
        _sensors_once_callback = None


def init(logger):
    global _log
    _log = logger

    state["arena"] = {"sensors": None}

    while not mqtt.client.is_connected:
        time.sleep(0.01)

    _log.info("Sending arena defaults.")
    signal_led(config.arena_defaults["signal_led"])
    day_lights(config.arena_defaults["day_lights"])

    mqtt.client.subscribe_callback(
        "arena/sensors", mqtt.mqtt_json_callback(_on_sensors)
    )
