"""
Arena hardware controller
Author: Tal Eisenberg, 2021

This module provides convenience functions for communicating with the arena hardware
over MQTT. It allows sending commands, and also stores sensor readings in the global state.
"""

import mqtt
import time
from subprocess import Popen, PIPE
import collections
import data_log
import json
from rl_logging import get_main_logger
import schedule
import logging
from configure import get_config

_state = None
_values_once_callback = None
_log: logging.Logger = None
_arena_log: data_log.DataLogger = None
_arena_state = None
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
    """Switch an external display on or off. Requires xrandr and an X server"""
    displays = get_config().arena["displays"]

    if display is None:
        if len(displays) == 0:
            _log.warn("Can't switch display on or off. No displays are defined.")
            return
        display_id = list(displays.values())[0]
        display = list(displays.keys())[0]
    else:
        display_id = displays[display]

    DISPLAY_CMD = f"DISPLAY={display_id} xrandr --output HDMI-0 --{{}}"
    _state["arena", "displays", display] = on

    if on:
        _run_shell_command(DISPLAY_CMD.format("auto"))
    else:
        _run_shell_command(DISPLAY_CMD.format("off"))


def run_command(command, interface, args=None, update_value=True):
    """
    Send a command to the MQTT-Serial bridge.

    Args:
    - command: The command name (str)
    - interface: The interface that should receive the command (str)
    - args: A list of command arguments (list of str)
    - update_value: When True, the value of the interface will be requested after sending the command.
                    It's generally a good idea in order to keep the system and arena interfaces in sync.
                    However, requesting values and waiting for a response after each command can reduce the
                    responsiveness of the arena controllers. Therefore, you might want to set this to False
                    when sending multiple commands over a short time period or when the interface has no value.
    """
    if args is None:
        js = json.dumps([command, interface])
    else:
        js = json.dumps([command, interface] + args)

    mqtt.client.publish(get_config().arena["command_topic"], js)
    if update_value:
        request_values(interface)


def request_values(interface=None):
    """
    Request the current value of an interface or of all interfaces (when interface=None).

    Args:
    - interface: Interface name (str) or None for requesting values from all interfaces.
    """
    topic = get_config().arena["command_topic"]
    if interface is None:
        mqtt.client.publish(topic, json.dumps(["get", "all"]))
    else:
        mqtt.client.publish(
            topic, json.dumps(["get", interface])
        )


def has_trigger():
    """Return True if a camera trigger arena interface is defined, or False otherwise"""
    return _trigger_interface is not None


def start_trigger(update_state=True):
    """
    Start the camera trigger if a trigger interface is defined.

    Args:
    - update_state: Whether to update the state store under ("video", "record", "ttl_trigger") to True (regardless of the actual trigger state).
    """
    if _trigger_interface is None:
        _log.warn("No trigger interface was found.")
        return

    if update_state:
        _state["video", "record", "ttl_trigger"] = True

    run_command("set", _trigger_interface, [1])


def stop_trigger(update_state=True):
    """
    Stop the camera trigger if a trigger interface is defined.

    Args:
    - update_state: Whether to update the state store under ("video", "record", "ttl_trigger") to False (regardless of the actual trigger state).
    """
    if _trigger_interface is None:
        _log.warn("No trigger interface was found.")
        return

    if update_state:
        _state["video", "record", "ttl_trigger"] = False

    run_command("set", _trigger_interface, [0])


def get_interfaces_config():
    """
    Return a list of all configured arena interfaces (a list of dicts). This is a single
    list of all interfaces configured over all Arduinos.
    """
    return _interfaces_config


def poll(callback_once=None):
    """
    Poll the arena controller state.

    Args:
    - callback_once: A function with a single argument that will be called once
                     the values arrive.
    """
    global _values_once_callback

    _values_once_callback = callback_once
    request_values()


def _flatten(d, parent_key="", sep="_"):
    if isinstance(d, collections.MutableMapping):
        items = []
        for k, v in d.items():
            new_key = str(parent_key) + sep + str(k) if parent_key else str(k)
            if isinstance(v, collections.MutableMapping) or isinstance(
                v, collections.MutableSequence
            ):
                items.extend(_flatten(v, new_key, sep=sep).items())
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
                items.extend(_flatten(v, new_key, sep=sep).items())
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

    data_log_config = get_config().arena.get("data_log", None)
    if data_log_config is not None:
        flat_values = _flatten(values)
        log_values = [timestamp]
        log_conf = data_log_config
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


def init(state):
    """
    Initialize the arena module.
    """
    global _state, _log, _arena_log, _arena_state, _interfaces_config, _trigger_interface
    _state = state
    _log = get_main_logger()
    _arena_state = state.get_cursor("arena")

    displays = get_config().arena["displays"]
    _arena_state.set_self(
        {
            "values": {},
            "timestamp": None,
            "displays": dict([(d, False) for d in displays.keys()]),
        }
    )

    for display in displays.keys():
        switch_display(False, display)

    try:
        with open(get_config().arena_config_path, "r") as f:
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

    data_log_config = get_config().arena.get("data_log", None)
    if data_log_config is not None:
        log_conf = data_log_config
        columns = [("time", "timestamptz not null")] + log_conf["columns"]
        _arena_log = data_log.QueuedDataLogger(
            db_table_name=log_conf["table_name"],
            columns=columns,
        )
        _arena_log.start()

    while not mqtt.client.is_connected:
        time.sleep(0.01)

    topic = get_config().arena["receive_topic"]
    mqtt.client.subscribe_callback(
        f"{topic}/all_values", mqtt.mqtt_json_callback(_on_all_values)
    )
    mqtt.client.subscribe_callback(f"{topic}/value", mqtt.mqtt_json_callback(_on_value))
    mqtt.client.subscribe_callback(f"{topic}/info/#", mqtt.mqtt_json_callback(_on_info))
    mqtt.client.subscribe_callback(
        f"{topic}/error/#", mqtt.mqtt_json_callback(_on_error)
    )

    poll()
    schedule.repeat(poll, get_config().arena["poll_interval"], pool="arena")


def shutdown():
    """
    Shutdown the arena module.
    """
    topic = get_config().arena["receive_topic"]
    mqtt.client.unsubscribe_callback(f"{topic}/all_values")
    mqtt.client.unsubscribe_callback(f"{topic}/info/#")
    mqtt.client.unsubscribe_callback(f"{topic}/error/#")
    if _arena_log:
        _arena_log.stop()
        _arena_log.join()
