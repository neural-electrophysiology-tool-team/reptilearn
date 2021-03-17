import mqtt
import state
import time

sensors_once_callback = None
log = None


def dispense_reward():
    mqtt.client.publish("arena/dispense_reward")


def signal_led(on):
    msg = "on" if on else "off"
    mqtt.client.publish("arena/signal_led", msg)


def day_lights(on):
    msg = "on" if on else "off"
    mqtt.client.publish("arena/day_lights", msg)


def line(idx, on):
    msg = "on" if on else "off"
    mqtt.client.publish(f"arena/line/{idx}", msg)


def sensors_poll(callback_once):
    global sensors_once_callback

    sensors_once_callback = callback_once
    mqtt.client.publish("arena/sensors/poll")


def sensors_set_interval(seconds):
    # not implemented i think
    mqtt.client.publish("arena/sensors/set_interval", seconds)


def on_sensors(_, reading):
    global sensors_once_callback
    
    reading["timestamp"] = time.time()

    state.update(("sensors",), reading)
    if sensors_once_callback is not None:
        sensors_once_callback(reading)
        sensors_once_callback = None


def init(logger):
    global log
    log = logger
    state.update(("sensors",), None)
    mqtt.client.subscribe_callback("arena/sensors", mqtt.mqtt_json_callback(on_sensors))

