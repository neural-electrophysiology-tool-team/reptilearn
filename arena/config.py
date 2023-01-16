import logging

# Use logging.DEBUG to log every message passed through the bridge.
log_level = logging.INFO

# Path of the arena configuration file. This is where the Arduinos behavior is configured.
arena_config_path = "../system/config/arena_config.json"

serial = {
    "ports": {
        # Configure each Arduino board. For example:
        # "arena": {
        #     "id": "<enter board hwid here>",
        #     "fqbn": "<enter board fqbn here>",
        # },
        # "camera_trigger": {
        #     "id": "<enter board hwid here>",
        #     "allow_get": False,
        #     "fqbn": "<enter board fqbn here>",
        # },
    },

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
