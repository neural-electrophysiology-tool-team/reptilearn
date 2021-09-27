import logging

log_level = logging.INFO

arena_config_path = "../system/config/arena_config.json"

serial = {
    "ports": {
        "arena": {
            "id": "1107E314515146544E4B2020FF0C3E57",
            "fqbn": "arduino:megaavr:nona4809",
        },
        "camera_trigger": {
            "id": "715B0511515146544E4B2020FF0C265A",
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
    "subscription": "arena_command",
    "publish_topic": "arena",
}
