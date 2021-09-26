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

try:
    bridge = SerialMQTTBridge(config.serial, config.mqtt, logger)
except Exception:
    logger.exception("Exception while initializing serial mqtt bridge:")
    exit(1)

try:
    while True:
        pass
except KeyboardInterrupt:
    logger.info("Shutting down...")
    bridge.shutdown()
