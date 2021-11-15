from state import state
from dynamic_loading import instantiate_class
import json
import video_write
from arena import start_trigger, stop_trigger
from datetime import datetime
from threading import Timer


video_config = None
image_sources = {}
image_observers = {}
video_writers = {}
_log = None
_config = None
_rec_state = None
_do_restore_trigger = False


def load_source(src_id, config):
    image_sources[src_id] = instantiate_class(
        config["class"],
        src_id,
        config,
        state_cursor=state.get_cursor(("video", "image_sources", src_id)),
    )


def load_observer(obs_id, config):
    image_observers[obs_id] = instantiate_class(
        config["class"],
        image_sources[config["src_id"]],
        config,
        state_cursor=state.get_cursor(("video", "image_observers", obs_id)),
    )


def load_video_config(config: dict):
    if "video" not in state:
        state["video"] = {
            "image_sources": {},
            "image_observers": {},
        }

    if "image_sources" in config:
        for src_id, conf in config["image_sources"].items():
            load_source(src_id, conf)

    if "image_observers" in config:
        for obs_id, conf in config["image_observers"].items():
            load_observer(obs_id, conf)


def load_video_writers():
    global video_writers
    video_writers = {}

    for src_id in image_sources.keys():
        src = image_sources[src_id]

        video_writers[src_id] = video_write.VideoWriter(
            src,
            frame_rate=_config.video_record["video_frame_rate"],
            encoding_params=_config.video_record["encoding_configs"][
                src.config["encoding_config"]
            ],
            queue_max_size=_config.video_record["max_write_queue_size"],
        )


def update_video_config(config: dict):
    global image_sources, image_observers, video_config
    shutdown_video()

    image_sources = {}
    image_observers = {}
    
    load_video_config(config)
    load_video_writers()

    start()

    _log.info(f"Saving video config to '{_config.video_config_path.resolve()}'...")
    with open(_config.video_config_path, "w") as f:
        json.dump(video_config, f, indent=4)

    video_config = config


def restore_after_experiment_session():
    _rec_state["write_dir"] = _config.media_dir
    _rec_state["filename_prefix"] = ""


def set_selected_sources(src_ids):
    _rec_state["selected_sources"] = src_ids


def select_source(src_id):
    if src_id in _rec_state["selected_sources"]:
        return

    _rec_state.append("selected_sources", src_id)


def unselect_source(src_id):
    if src_id in _rec_state["selected_sources"]:
        _rec_state.remove("selected_sources", src_id)


def start_record(src_ids=None):
    global _do_restore_trigger

    if _rec_state["is_recording"] is True:
        return

    if src_ids is None:
        src_ids = _rec_state["selected_sources"]

    if len(src_ids) == 0:
        return

    def standby():
        _rec_state["is_recording"] = True
        for src_id in src_ids:
            video_writers[src_id].start_observing()

    if _rec_state["ttl_trigger"]:
        _do_restore_trigger = True
        stop_trigger(update_state=False)
        Timer(1, start_trigger, kwargs={"update_state": False}).start()

    Timer(0.5, standby).start()


def stop_record(src_ids=None):
    global _do_restore_trigger
    if _rec_state["is_recording"] is False:
        return

    if src_ids is None:
        src_ids = _rec_state["selected_sources"]

    if len(src_ids) == 0:
        return

    def stop():
        _rec_state["is_recording"] = False
        for src_id in src_ids:
            video_writers[src_id].stop_observing()

    if _do_restore_trigger:
        stop_trigger(update_state=False)
        Timer(1, start_trigger, kwargs={"update_state": False}).start()
        _do_restore_trigger = False

    Timer(0.5, stop).start()


def capture_images(src_ids=None):
    if src_ids is None:
        src_ids = _rec_state["selected_sources"]

    selected_sources = [image_sources[src_id] for src_id in src_ids]
    timestamp = datetime.now()

    for src in selected_sources:
        p = video_write.save_image(src, timestamp)
        _log.info(f"Saved image from {src} to {p}")


def init(log, config):
    global _log, _config, video_config, _rec_state
    _log = log
    _config = config
    config_path = config.video_config_path

    if "video" not in state:
        state["video"] = {
            "image_sources": {},
            "image_observers": {},
        }

    _rec_state = state.get_cursor(("video", "record"))
    _rec_state.set_self(
        {
            "selected_sources": [],
            "is_recording": False,
            "write_dir": _config.media_dir,
            "filename_prefix": "",
        }
    )

    if not config_path.exists():
        video_config = {}
    else:
        try:
            with open(config_path, "r") as f:
                video_config = json.load(f)
        except Exception:
            log.exception(f"Exception while reading {str(config_path)}")
            return

    load_video_config(video_config)
    load_video_writers()

    ttl_trigger = _config.video_record["start_trigger_on_startup"]
    if ttl_trigger:
        start_trigger()
    else:
        stop_trigger()


def update_acquire_callback(src_id):
    def select_when_acquiring(old_val, new_val):
        nonlocal src_id

        if new_val is True and old_val is False:
            select_source(src_id)
        elif new_val is False and old_val is True:
            unselect_source(src_id)

    state.add_callback(
        ("video", "image_sources", src_id, "acquiring"), select_when_acquiring
    )


def start():
    """
    Start processes of image writers, observers and sources
    """

    for w in video_writers.values():
        w.start()

    _log.info(f"Starting image observers: {', '.join(list(image_observers.keys()))}")
    for img_obs in image_observers.values():
        img_obs.start()

    _log.info(f"Starting image sources: {', '.join(list(image_sources.keys()))}")
    for src_id, img_src in image_sources.items():
        img_src.start()
        update_acquire_callback(src_id)


def shutdown_video():
    for w in video_writers.values():
        w.stop_observing()
        w.shutdown()
        w.join()

    for obs in image_observers.values():
        obs.stop_observing()
        obs.shutdown()
        obs.join()

    start_trigger()
    for img_src in image_sources.values():
        img_src.stop_event.set()
        img_src.join()

    for src_id in image_sources.keys():
        state.remove_callback(("video", "image_sources", src_id, "acquiring"))


def shutdown():
    shutdown_video()
    stop_trigger()
