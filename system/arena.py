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
import json
import schedule


_values_once_callback = None
_log = None
_arena_state = None


def _run_shell_command(cmd):
    """Execute shell command"""
    process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        _log.info(f'Error running cmd: "{cmd}"; {stderr}')
    return stdout.decode("ascii")


def turn_touchscreen(on, display):
    display_id = _config.arena["displays"][display]
    DISPLAY_CMD = f"DISPLAY={display_id} xrandr --output HDMI-0 --{{}}"
    state["arena", "touchscreen"] = on

    if on:
        _run_shell_command(DISPLAY_CMD.format("auto"))
    else:
        _run_shell_command(DISPLAY_CMD.format("off"))


def run_command(command, interface, args=None, update_value=False):
    if args is None:
        js = json.dumps([command, interface])
    else:
        js = json.dumps([command, interface] + args)

    mqtt.client.publish("arena/command", js)
    if update_value:
        request_values(interface)


def request_values(interface=None):
    if interface is None:
        mqtt.client.publish("arena/command", json.dumps(["get", "all"]))
    else:
        mqtt.client.publish("arena/command", json.dumps(["get", interface]))


def get_value(interface):
    return _arena_state["values", interface]


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


def poll(callback_once=None):
    """
    Poll the arena controller state.
    - callback_once: A function with a single argument that will be called once
                     the values arrive.
    """
    global _values_once_callback

    _values_once_callback = callback_once
    request_values()


def _on_all_values(_, values):
    global _values_once_callback

    values["timestamp"] = time.time()

    _arena_state["values"] = values

    if _values_once_callback is not None:
        _values_once_callback(values)
        _values_once_callback = None

    # _sensor_log.log(
    #    (
    #        reading["timestamp"],
    #         reading["temp"][0],
    #         reading["temp"][1],
    #         reading["temp"][2],
    #         reading["humidity"],
    #     )
    # )


def _on_value(_, msg):
    interface, value = list(msg.items())[0]
    _arena_state["values", interface] = value


def _on_info(topic, msg):
    _log.info(f"[{topic}] {msg}")


def _on_error(topic, msg):
    _log.error(f"[{topic}] {msg}")


def init(logger, config):
    """
    Initialize the arena module.
    Connects to MQTT, inits sensor data logger, sends arena defaults, and subscribes for
    sensor updates.

    - arena_defaults: A dict with signal_led and day_lights keys with default values.
    """
    global _log, _arena_log, _config, _arena_state
    _log = logger
    _config = config
    _arena_state = state.get_cursor("arena")
    _arena_state.set_self({"values": {}})

    try:
        with open(config.arena_config_path, "r") as f:
            arena_config = json.load(f)
            _arena_state["config"] = arena_config
    except json.JSONDecodeError:
        _log.exception("Exception while parsing arena config")
        return

    # NOTE: This data logger is specific to arena sensor reading format.
    # _arena_log = data_log.QueuedDataLogger(
    #     table_name="arena",
    #     log_to_db=True,
    #     columns=(
    #         ("time", "timestamptz not null"),
    #         ("temp0", "double precision"),
    #         ("temp1", "double precision"),
    #         ("temp2", "double precision"),
    #         ("humidity", "double precision"),
    #     ),
    # )
    # _arena_log.start()

    while not mqtt.client.is_connected:
        time.sleep(0.01)

    mqtt.client.subscribe_callback(
        "arena/all_values", mqtt.mqtt_json_callback(_on_all_values)
    )
    mqtt.client.subscribe_callback("arena/value", mqtt.mqtt_json_callback(_on_value))
    mqtt.client.subscribe_callback("arena/info/#", mqtt.mqtt_json_callback(_on_info))
    mqtt.client.subscribe_callback("arena/error/#", mqtt.mqtt_json_callback(_on_error))

    poll()
    schedule.repeat(poll, config.arena["poll_interval"], pool="arena")


def release():
    mqtt.client.unsubscribe_callback("arena/values")
    mqtt.client.unsubscribe_callback("arena/info/#")
    mqtt.client.unsubscribe_callback("arena/error/#")
    # _arena_log.stop()
    # _arena_log.join()
