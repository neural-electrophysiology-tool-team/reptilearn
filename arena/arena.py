"""
Serial-MQTT Bridge.
author: Tal Eisenberg <eisental@gmail.com>

Run `python main.py --help` for more information.
"""

import importlib
import json
import logging
import sys
import subprocess
import argparse
import platform
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


def upload_program(log, serial_ports_config, port_name=None):
    if len(serial_ports_config) == 0:
        log.error("Nothing to upload. Please define your Arduino serial ports in the config module")
        return False

    if port_name is not None and port_name not in serial_ports_config:
        log.error(f"Unknown port name: {port_name}")
        return False

    def upload(port_name, port_conf):
        pid = port_conf["serial_number"]

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

            return ret == 0
        except Exception:
            log.exception("Exception while uploading program:")
            return False

    errored = False
    if port_name is None:
        for pn, pc in serial_ports_config.items():
            if upload(pn, pc):
                log.info("Upload successful!")
            else:
                log.error(f"Error uploading program over serial port {pn} (sn: {pc['serial_number']})")
                errored = True
    else:
        port_conf = serial_ports_config[port_name]
        if upload(port_name, port_conf):
            log.info("Upload successful!")
        else:
            log.error(f"Error uploading program over serial port {port_name} (sn: {port_conf['serial_number']})")
            errored = True

    return not errored


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Serial-MQTT Bridge",
        epilog="Routes messages between mqtt clients and arduino devices over serial ports.",
    )
    arg_parser.add_argument(
        "--list-ports", help="List available serial ports", action="store_true"
    )
    arg_parser.add_argument(
        "--list-ports-json", help="List available serial ports in JSON format", action="store_true"
    )
    arg_parser.add_argument(
        "--upload",
        help="Upload arena program to all devices. Requires arduino-cli.",
        default="",
        nargs="?",
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

    # load arena config
    arena_conf = None
    try:
        with open(config.arena_config_path, "r") as f:
            arena_conf = json.load(f)
    except json.JSONDecodeError as e:
        logger.exception(f"While decoding {config.arena_config_path}:")
        raise e

    if type(arena_conf) is not dict:
        raise ValueError("The arena config json root is expected to be an object.")

    if args.list_ports:
        ports = list_ports.comports()
        print("Available serial ports:\n")
        for port in ports:
            if port.serial_number is None:
                continue
            print(f'\t{port.device}: {port.description}, serial number: "{port.serial_number}"')

        sys.exit(0)

    if args.list_ports_json:
        ports = list_ports.comports()
        print(json.dumps([{"device": p.device, "description": p.description, "serial_number": p.serial_number} for p in ports if p.serial_number is not None]))
        sys.exit(0)

    if args.upload is None or len(args.upload) > 0:
        upload_ret = upload_program(logger, arena_conf, args.upload)
        if upload_ret is True:
            sys.exit(0)
        else:
            sys.exit(1)

    if len(arena_conf) == 0:
        logger.error("There are no configured serial ports. Exiting.")

    try:
        bridge = SerialMQTTBridge(config, arena_conf, logger)
    except Exception:
        logger.exception("Exception while initializing serial mqtt bridge:")
        sys.exit(1)

    try:
        bridge.wait()
    except KeyboardInterrupt:
        pass
    finally:
        bridge.shutdown()
