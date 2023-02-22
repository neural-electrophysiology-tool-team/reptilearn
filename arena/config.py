import logging

# Use logging.DEBUG to log every message passed through the bridge.
log_level = logging.INFO

# Path of the arena configuration file.
arena_config_path = "../system/config/arena_config.json"

# Serial communication settings
serial = {
    # Serial port baud rate. Do not change unless you really want to.
    "baud_rate": 115200,
}

# MQTT settings
mqtt = {
    # Server host and port number
    "host": "localhost",
    "port": 1883,

    # MQTT topics for outgoing commands and incoming data.
    "command_topic": "arena_command",
    "publish_topic": "arena",
}
