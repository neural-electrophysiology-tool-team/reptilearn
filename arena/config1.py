import logging

log_level = logging.INFO

arena_config_path = "../system/config/arena_config1.json"

serial = {
    "ports": {
        "arena": {
            "id": "5B7C77B551514746324B2020FF0C0726",
            "fqbn": "arduino:megaavr:nona4809",
        },
        "camera_trigger": {
            "id": "BF7C1CDF51514746324B2020FF0D092C",
            "allow_get": False,
            "fqbn": "arduino:megaavr:nona4809",
        },
    },
    "baud_rate": 115200,
}

# MQTT server address
mqtt = {
    "host": "localhost",
    "port": 1883,
    "command_topic": "arena_command",
    "publish_topic": "arena",
}
