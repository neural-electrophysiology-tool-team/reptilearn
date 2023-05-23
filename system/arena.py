"""
Arena hardware controller
Author: Tal Eisenberg, 2021

This module provides convenience functions for communicating with the arena hardware
over MQTT. It allows sending commands, and also stores sensor readings in the global state.
"""

import shutil
import threading
import mqtt
import time
from subprocess import STDOUT, Popen, PIPE
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
_arena_config: dict = None
_interfaces_config: list = None
_trigger_interface: str = None
_arena_process = None
_arena_process_thread = None


def _execute(command, cwd=None, shell=False, log=True):
    """Run external program as a subprocess"""
    process = Popen(
        command,
        shell=shell,
        cwd=cwd,
        universal_newlines=True,
        stdout=PIPE,
        stderr=STDOUT,
    )
    output = ""

    # Poll process for new output until finished
    for line in process.stdout:
        if line:
            line = line.rstrip()
            if log:
                _log.info(line)
            output += line

    process.wait()

    if process.returncode == 0:
        return output
    else:
        raise Exception(command, process.returncode, output)


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
        _execute(DISPLAY_CMD.format("auto"), shell=True)
    else:
        _execute(DISPLAY_CMD.format("off"), shell=True)


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


def request_values(interface=None, port_name=None):
    """
    Request the current value of an interface or of all interfaces (when interface=None).

    Args:
    - interface: Interface name (str) or None for requesting values from all interfaces.
    - port_name: Request values from all interfaces defined on the specified port. Interface must be None.
    """
    topic = get_config().arena["command_topic"]
    if interface is None:
        mqtt.client.publish(
            topic,
            json.dumps(
                ["get", "all"] if port_name is None else ["get", "all", port_name]
            ),
        )
    else:
        mqtt.client.publish(topic, json.dumps(["get", interface]))


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


def get_arena_config():
    """
    Return a dictionary containing the arena config as read from the config file.
    """
    return _arena_config


def get_interfaces_config():
    """
    Return a list of all configured arena interfaces (a list of dicts). This is a single
    list of all interfaces configured over all Arduino boards.
    """
    return _interfaces_config


def update_arena_config(arena_conf):
    """
    Update the arena config file with the supplied dictionary.
    On success reload the configuration from the config file.
    """
    shutil.move(
        get_config().arena_config_path,
        get_config().arena_config_path.parent
        / f"{get_config().arena_config_path.name}.OLD",
    )

    with open(get_config().arena_config_path, "w") as f:
        json.dump(arena_conf, f, indent=4)

    load_arena_config()


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
    if isinstance(d, collections.abc.MutableMapping):
        items = []
        for k, v in d.items():
            new_key = str(parent_key) + sep + str(k) if parent_key else str(k)
            if isinstance(v, collections.abc.MutableMapping) or isinstance(
                v, collections.abc.MutableSequence
            ):
                items.extend(_flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))

        return dict(items)

    elif isinstance(d, collections.abc.MutableSequence):
        items = []
        for i, v in enumerate(d):
            new_key = parent_key + sep + str(i)
            if isinstance(v, collections.abc.MutableMapping) or isinstance(
                v, collections.abc.MutableSequence
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

    timestamp = time.time()
    _arena_state["timestamp"] = timestamp


def _on_info(topic, msg):
    _log.info(f"[{topic}] {msg}")


def _on_error(topic, msg):
    _log.error(f"[{topic}] {msg}")


def _on_listening_status(_, is_listening):
    _init_arena_state()
    _arena_state["bridge", "listening"] = is_listening
    if is_listening:
        poll()


def run_mqtt_serial_bridge():
    """
    Run and start communication with the arena controller on a separate thread.
    """
    global _arena_process_thread

    if _arena_process is not None:
        _log.error("Can't run arena controller. It is already running.")
        return

    dir = get_config().arena_controller_path
    cmd = ["python", "arena.py"]

    def bridge_comm_thread():
        global _arena_process
        _log.info("Running arena controller...")
        _arena_process = Popen(
            cmd, cwd=dir, stdout=PIPE, stderr=STDOUT, universal_newlines=True
        )
        _arena_state["bridge", "running"] = True
        _log.info(f"Arena controller is running. pid: {_arena_process.pid}")
        stdout, _ = _arena_process.communicate()

        if _arena_process.returncode != 0:
            _log.info(
                f"Arena controller terminated (exit code {_arena_process.returncode})"
            )
        else:
            _log.info("Arena controller terminated")

        _arena_state["bridge", "running"] = False
        _arena_process = None

    _arena_process_thread = threading.Thread(target=bridge_comm_thread)
    _arena_process_thread.start()


def stop_mqtt_serial_bridge():
    """
    Stop the arena controller subprocess.
    """
    global _arena_process, _arena_process_thread
    if _arena_process is not None:
        run_command("terminate", "bridge", [], False)
        _arena_process_thread.join(timeout=4)

        if _arena_process_thread.is_alive():
            _log.warn(
                "Arena controller graceful termination was unsuccessful. Terminating process directly..."
            )
            _arena_process.terminate()
            _arena_process_thread.join()
            _log.info("Arena controller process terminated.")

        _arena_process_thread = None


def restart_mqtt_serial_bridge():
    trigger_on = has_trigger() and _state["video", "record", "ttl_trigger"]
    stop_mqtt_serial_bridge()
    run_mqtt_serial_bridge()

    def on_listening(_, new):
        if new and trigger_on:
            _log.info("Restarting trigger")
            start_trigger()
            _state.remove_callback(("arena", "bridge", "listening"))

    _state.add_callback(("arena", "bridge", "listening"), on_listening)


def get_ports():
    """
    Return a list containing all available serial ports. Each port is represented by a dictionary
    with `description, device, serial_number` keys
    """
    ret = _execute(
        ["python", "arena.py", "--list-ports-json"],
        cwd=get_config().arena_controller_path,
        log=False,
    )
    return json.loads(ret)


def upload_program(port_name=None):
    """
    Upload the Arduino program over serial port `port_name`. If `port_name` is None
    Upload to all configured ports.
    """
    if _arena_state["bridge", "uploading"]:
        raise Exception("Can't upload program. Already uploading.")
    if _arena_state["bridge", "running"]:
        was_running = True
        stop_mqtt_serial_bridge()
    else:
        was_running = False

    def upload_thread():
        _log.info("Uploading program to Arduino boards...")

        if port_name is not None:
            cmd = ["python", "arena.py", "--upload", port_name]
        else:
            cmd = ["python", "arena.py", "--upload"]

        try:
            _arena_state["bridge", "uploading"] = True
            _execute(cmd, cwd=get_config().arena_controller_path)
        except Exception:
            _log.exception("Exception while uploading program:")
        finally:
            _arena_state["bridge", "uploading"] = False
            if was_running:
                run_mqtt_serial_bridge()

        _log.info("Done uploading.")

    threading.Thread(target=upload_thread).start()


def _init_arena_state():
    displays = get_config().arena["displays"]
    if not _arena_state.exists(()):
        _arena_state.set_self({})
    _arena_state["values"] = {}
    _arena_state["timestamp"] = None
    _arena_state["displays"] = dict([(d, False) for d in displays.keys()])


def _init_bridge_state():
    _arena_state["bridge"] = {
        "running": False,
        "listening": False,
        "uploading": False,
    }


def load_arena_config():
    """
    Load arena config from file.
    """
    global _interfaces_config, _arena_config, _trigger_interface

    try:
        with open(get_config().arena_config_path, "r") as f:
            arena_config = json.load(f)
            interfaces_config = []
            for port_config in arena_config.values():
                interfaces_config += port_config["interfaces"]

    except json.JSONDecodeError:
        _log.exception("Exception while parsing arena config:")
        return

    _interfaces_config = interfaces_config
    _arena_config = arena_config

    had_trigger = has_trigger()

    _trigger_interface = None
    for ifs in _interfaces_config:
        if ifs["type"] == "trigger":
            _trigger_interface = ifs["name"]
            break

    if _state.get(("video", "record"), default=None) is not None:
        if _trigger_interface and not had_trigger:
            stop_trigger()
        elif _trigger_interface is None and had_trigger:
            _state.delete(("video", "record", "ttl_trigger"))


def init(state):
    """
    Initialize the arena module.
    """
    global _state, _log, _arena_log, _arena_state
    _state = state
    _log = get_main_logger()
    _arena_state = state.get_cursor("arena")

    _init_arena_state()

    if not get_config().arena_config_path.exists():
        with open(get_config().arena_config_path, "w") as f:
            json.dump({}, f)

    load_arena_config()

    data_log_config = get_config().arena.get("data_log", None)
    if data_log_config is not None:
        log_conf = data_log_config
        columns = [("time", "timestamptz not null")] + log_conf["columns"]
        _arena_log = data_log.QueuedDataLogger(
            db_table_name=log_conf["table_name"],
            columns=columns,
        )
        _arena_log.start()

    _init_bridge_state()

    if mqtt.client.connection_failed:
        _log.warn("MQTT connection failed. Can't connect to arena controller.")
        return

    topic = get_config().arena["receive_topic"]
    mqtt.client.subscribe_callback(
        f"{topic}/all_values", mqtt.mqtt_json_callback(_on_all_values)
    )
    mqtt.client.subscribe_callback(f"{topic}/value", mqtt.mqtt_json_callback(_on_value))
    mqtt.client.subscribe_callback(f"{topic}/info/#", mqtt.mqtt_json_callback(_on_info))
    mqtt.client.subscribe_callback(
        f"{topic}/error/#", mqtt.mqtt_json_callback(_on_error)
    )
    mqtt.client.subscribe_callback(
        f"{topic}/listening", mqtt.mqtt_json_callback(_on_listening_status)
    )

    if len(_arena_config) > 0 and get_config().arena["run_controller"] is True:
        run_mqtt_serial_bridge()

    if _arena_state["bridge", "listening"] is False:
        run_command("is_listening", "bridge", [], False)

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

    stop_mqtt_serial_bridge()
