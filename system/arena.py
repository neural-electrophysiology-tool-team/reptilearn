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
import collections
import data_log
import json
import schedule
import logging


_values_once_callback = None
_log: logging.Logger = None
_arena_log: data_log.DataLogger = None
_arena_state = None
_config = None
_interfaces_config: list = None
_trigger_interface: dict = None


def _run_shell_command(cmd):
    """Execute shell command"""
    process = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        _log.info(f'Error running cmd: "{cmd}"; {stderr}')
    return stdout.decode("ascii")


def switch_display(on, display=None):
    if display is None:
        display_id = list(_config.arena["displays"].values())[0]
        display = list(_config.arena["displays"].keys())[0]
    else:
        display_id = _config.arena["displays"][display]

    DISPLAY_CMD = f"DISPLAY={display_id} xrandr --output HDMI-0 --{{}}"
    state["arena", "displays", display] = on

    if on:
        _run_shell_command(DISPLAY_CMD.format("auto"))
    else:
        _run_shell_command(DISPLAY_CMD.format("off"))


def run_command(command, interface, args=None, update_value=True):
    if args is None:
        js = json.dumps([command, interface])
    else:
        js = json.dumps([command, interface] + args)

    mqtt.client.publish(_config.arena["command_topic"], js)
    if update_value:
        request_values(interface)


def request_values(interface=None):
    if interface is None:
        mqtt.client.publish(_config.arena["command_topic"], json.dumps(["get", "all"]))
    else:
        mqtt.client.publish(
            _config.arena["command_topic"], json.dumps(["get", interface])
        )


def get_value(interface):
    return _arena_state["values", interface]


def start_trigger(update_state=True):
    if _trigger_interface is None:
        _log.info("No trigger interface was found.")
        return

    if update_state:
        state["video", "record", "ttl_trigger"] = True

    run_command("set", _trigger_interface, [1])


def stop_trigger(update_state=True):
    if _trigger_interface is None:
        _log.info("No trigger interface was found.")
        return

    if update_state:
        state["video", "record", "ttl_trigger"] = False

    run_command("set", _trigger_interface, [0])


def get_interfaces_config():
    return _interfaces_config


def poll(callback_once=None):
    """
    Poll the arena controller state.
    - callback_once: A function with a single argument that will be called once
                     the values arrive.
    """
    global _values_once_callback

    _values_once_callback = callback_once
    request_values()


def flatten(d, parent_key="", sep="_"):
    if isinstance(d, collections.MutableMapping):
        items = []
        for k, v in d.items():
            new_key = str(parent_key) + sep + str(k) if parent_key else str(k)
            if isinstance(v, collections.MutableMapping) or isinstance(
                v, collections.MutableSequence
            ):
                items.extend(flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))

        return dict(items)

    elif isinstance(d, collections.MutableSequence):
        items = []
        for i, v in enumerate(d):
            new_key = parent_key + sep + str(i)
            if isinstance(v, collections.MutableMapping) or isinstance(
                v, collections.MutableSequence
            ):
                items.extend(flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    else:
        return d


def _on_all_values(_, values):
    global _values_once_callback

    timestamp = time.time()
    _arena_state["timestamp"] = timestamp
    _arena_state.update("values", values)

    if _values_once_callback is not None:
        _values_once_callback(values)
        _values_once_callback = None

    if "data_log" in _config.arena:
        flat_values = flatten(values)
        log_values = [timestamp]
        log_conf = _config.arena["data_log"]
        for col in log_conf["columns"]:
            if col[0] in flat_values:
                log_values.append(flat_values[col[0]])
            else:
                log_values.append(None)

        _arena_log.log(log_values)


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
    global _log, _arena_log, _config, _arena_state, _interfaces_config, _trigger_interface
    _log = logger
    _config = config
    _arena_state = state.get_cursor("arena")
    _arena_state.set_self(
        {
            "values": {},
            "timestamp": None,
            "displays": dict([(d, False) for d in config.arena["displays"].keys()]),
        }
    )

    for display in config.arena["displays"].keys():
        switch_display(False, display)

    try:
        with open(config.arena_config_path, "r") as f:
            arena_config = json.load(f)
            interfaces_config = []
            for interfaces in arena_config.values():
                interfaces_config += interfaces

    except json.JSONDecodeError:
        _log.exception("Exception while parsing arena config:")
        return

    _interfaces_config = interfaces_config

    for ifs in interfaces_config:
        if ifs["type"] == "trigger":
            _trigger_interface = ifs["name"]
            break

    if "data_log" in config.arena:
        log_conf = config.arena["data_log"]
        columns = [("time", "timestamptz not null")] + log_conf["columns"]
        _arena_log = data_log.QueuedDataLogger(
            table_name=log_conf["table_name"],
            log_to_db=True,
            columns=columns,
        )
        _arena_log.start()

    while not mqtt.client.is_connected:
        time.sleep(0.01)

    topic = config.arena["receive_topic"]
    mqtt.client.subscribe_callback(
        f"{topic}/all_values", mqtt.mqtt_json_callback(_on_all_values)
    )
    mqtt.client.subscribe_callback(f"{topic}/value", mqtt.mqtt_json_callback(_on_value))
    mqtt.client.subscribe_callback(f"{topic}/info/#", mqtt.mqtt_json_callback(_on_info))
    mqtt.client.subscribe_callback(
        f"{topic}/error/#", mqtt.mqtt_json_callback(_on_error)
    )

    poll()
    schedule.repeat(poll, config.arena["poll_interval"], pool="arena")


def shutdown():
    topic = _config.arena["receive_topic"]
    mqtt.client.unsubscribe_callback(f"{topic}/all_values")
    mqtt.client.unsubscribe_callback(f"{topic}/info/#")
    mqtt.client.unsubscribe_callback(f"{topic}/error/#")
    _arena_log.stop()
    _arena_log.join()
