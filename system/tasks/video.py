import video_system


def start_record(log):
    log.info("Starting video recording.")
    video_system.start_record()


def stop_record(log):
    log.info("Stopping video recording.")
    video_system.stop_record()
