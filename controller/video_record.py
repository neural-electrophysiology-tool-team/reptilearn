from video_stream import VideoWriter
from pathlib import Path
import mqtt
from threading import Timer

# TODO
# - take fps from image source if possible, allow custom fps


video_writers = {}

mqtt_client = mqtt.Client()


def init(image_sources):
    for img_src in image_sources:
        video_writers[img_src.src_id] = VideoWriter(img_src, fps=60, write_path=Path("videos"))

    mqtt_client.connect()
    
    for w in video_writers.values():
        w.start()


def start_trigger(pulse_len=17):
    mqtt_client.publish_json("arena/ttl_trigger/start", {"pulse_len": pulse_len})


def stop_trigger():
    mqtt_client.publish("arena/ttl_trigger/stop")


def start_record(src_ids=None):
    if src_ids is None:
        src_ids = video_writers.keys()

    def standby():
        for src_id in src_ids:
            video_writers[src_id].start_writing()

    stop_trigger()
    Timer(0.5, standby).start()
    Timer(1, start_trigger).start()


def stop_record(src_ids=None):
    if src_ids is None:
        src_ids = video_writers.keys()

    def stop():
        for src_id in src_ids:
            video_writers[src_id].stop_writing()

    stop_trigger()
    Timer(0.5, stop).start()
