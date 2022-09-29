import video_system
from rl_logging import get_main_logger

log = get_main_logger()


def start_record():
    log.info("Starting video recording.")
    video_system.start_record()


def stop_record():
    log.info("Stopping video recording.")
    video_system.stop_record()
