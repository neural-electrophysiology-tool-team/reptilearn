import logging

log_level = logging.DEBUG

# Serial ports for a camera trigger device and any number of devices
# communicating using json messages.
serial = {
    "config_path": "../system/config/arena_config.json",
    "ports": {
        "arena": {
            "id": "1107E314515146544E4B2020FF0C3E57",
        },
        "camera_trigger": {
            "id": "715B0511515146544E4B2020FF0C265A",
            "allow_get": False,
        },
    },
    "baud_rate": 115200,
}

# MQTT server address
mqtt = {
    "host": "localhost",
    "port": 1883,
    "subscription": "arena/command",
    "publish_topic": "arena",
}
