import logging
import sys
from serial_mqtt import SerialMQTTBridge
import config

# logging configs
logging.basicConfig(
    stream=sys.stdout,
    level=config.log_level,
    format="[%(levelname)s] - %(asctime)s: %(message)s",
)
logger = logging.getLogger("Arena")

bridge = SerialMQTTBridge(config.serial, config.mqtt, logger)

try:
    while True:
        pass
except KeyboardInterrupt:
    logger.info("Shutting down...")
    bridge.shutdown()
