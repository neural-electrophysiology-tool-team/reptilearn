import logging

log_level = logging.INFO

# Serial ports for a camera trigger device and any number of devices
# communicating using json messages.
serial = {
    "camera_trigger_port": "715B0511515146544E4B2020FF0C265A",
    "ports": [
        {
            "name": "arena",
            "id": "1107E314515146544E4B2020FF0C3E57",
            "config_path": "../system/config/arena_config.json",
        }
    ],
    "baud_rate": 115200,
}

# MQTT server address
mqtt = {
    "host": "localhost",
    "port": 1883,
    "subscription": "arena/command",
    "publish_topic": "arena",
}
