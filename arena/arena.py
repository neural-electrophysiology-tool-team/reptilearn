import logging
import sys
import subprocess
import argparse
import platform
from serial.tools import list_ports
from serial_mqtt import SerialMQTTBridge, serial_port_by_id
import config

"""
Serial-MQTT Bridge.
author: Tal Eisenberg (2021)

Run `python main.py --help` for more information.
"""


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
    for port_name, port_conf in serial_ports_config.items():
        pid = port_conf["id"]

        if "fqbn" not in port_conf:
            log.error(f"Missing 'fqbn' key in port '{port_name}' config.")
            return False

        try:
            file_flag = "-f" if platform.system() == "Darwin" else "-F"

            port = serial_port_by_id(pid)
            log.info(f"Uploading arena program to port '{port_name}' ({port}).")
            ret = run_shell_command(log, ["stty", file_flag, port.device, "1200"])
            if ret != 0:
                return False

            ret = run_shell_command(
                log,
                [
                    "arduino-cli",
                    "compile",
                    "--fqbn",
                    port_conf["fqbn"],
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
                    port_conf["fqbn"],
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
    logger = logging.getLogger("Arena")
    logging.basicConfig(
        stream=sys.stdout,
        level=config.log_level,
        format="[%(levelname)s] - %(asctime)s: %(message)s",
    )

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
    args = arg_parser.parse_args()

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

    try:
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bridge.shutdown()
