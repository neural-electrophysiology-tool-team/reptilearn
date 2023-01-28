"""
Serial-MQTT Bridge.
author: Tal Eisenberg <eisental@gmail.com>

Run `python main.py --help` for more information.
"""

import importlib
import logging
import sys
import subprocess
import argparse
import platform
import threading
import traceback
from serial.tools import list_ports
from serial_mqtt import SerialMQTTBridge, serial_port_by_id


def load_config(config_name: str):
    """
    Loads a config module from <config_name>.py.

    Return the new global config module.
    """
    try:
        config = importlib.import_module(config_name)
    except Exception:
        traceback.print_exc()
        sys.exit(1)

    return config


def run_shell_command(log, cmd):
    ret = subprocess.call(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    if ret != 0:
        log.error(f"Nonzero exit code while running {' '.join(cmd)}")
    return ret


def upload_program(log, serial_ports_config):
    if len(serial_ports_config) == 0:
        log.error("Nothing to upload. Please define your Arduino serial ports in the config module")
        return False

    for port_name, port_conf in serial_ports_config.items():
        pid = port_conf["id"]

        if "fqbn" not in port_conf:
            log.error(f"Missing 'fqbn' key in port '{port_name}' config.")
            return False

        try:
            file_flag = "-f" if platform.system() == "Darwin" else "-F"

            port = serial_port_by_id(pid)
            log.info(f"Uploading arena program to port '{port_name}' ({port}).")

            if platform.system() != "Windows":
                ret = run_shell_command(log, ["stty", file_flag, port.device, "1200"])
                if ret != 0:
                    return False

            ret = run_shell_command(
                log,
                [
                    "arduino-cli",
                    "compile",
                    "--fqbn",
                    str(port_conf["fqbn"]).strip(),
                    "arduino_arena",
                ],
            )
            if ret != 0:
                return False

            ret = run_shell_command(
                log,
                [
                    "arduino-cli",
                    "upload",
                    "-p",
                    port.device,
                    "--fqbn",
                    str(port_conf["fqbn"]).strip(),
                    "arduino_arena",
                ],
            )
            if ret != 0:
                return False

        except Exception:
            log.exception("Exception while uploading program:")
            return False

    log.info("Done uploading!")
    return True


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Serial-MQTT Bridge",
        epilog="Routes messages between mqtt clients and arduino devices over serial ports.",
    )
    arg_parser.add_argument(
        "--list-ports", help="List available serial ports", action="store_true"
    )
    arg_parser.add_argument(
        "--upload",
        help="Upload arena program to all devices. Requires arduino-cli.",
        action="store_true",
    )
    arg_parser.add_argument(
        "--config",
        help="Config module name",
        default="config",
    )
    args = arg_parser.parse_args()

    config = load_config(args.config)

    logger = logging.getLogger("Arena")
    logging.basicConfig(
        stream=sys.stdout,
        level=config.log_level,
        format="[%(levelname)s] - %(asctime)s: %(message)s",
    )

    if args.list_ports:
        ports = list_ports.comports()
        print("Available serial ports:\n")
        for port in ports:
            print(f'\t{port.device}: {port.description}, hwid="{port.hwid}"')
        print("\nPort id can be any unique string contained in the port's hwid string.")
        sys.exit(0)

    if args.upload:
        upload_ret = upload_program(logger, config.serial["ports"])
        if upload_ret is True:
            sys.exit(0)
        else:
            sys.exit(1)

    try:
        bridge = SerialMQTTBridge(config, logger)
    except Exception:
        logger.exception("Exception while initializing serial mqtt bridge:")
        sys.exit(1)

    forever = threading.Event()
    try:
        forever.wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bridge.shutdown()
