from state import state
from dynamic_loading import instantiate_class, load_modules, find_subclasses
import video_write
from arena import has_trigger, start_trigger, stop_trigger
from video_stream import ImageSource, ImageObserver
import overlay
from threading import Timer
from pathlib import Path
import json


video_config = None
image_sources = {}
image_observers = {}
video_writers = {}
source_classes = []
observer_classes = []
image_class_params = {}

_log = None
_config = None
_rec_state = None
_do_restore_trigger = False


def load_source(id, config):
    image_sources[id] = instantiate_class(
        config["class"],
        id,
        config,
        state_cursor=state.get_cursor(("video", "image_sources", id)),
    )

    overlay.overlays[id] = [overlay.TimestampVisualizer()]


def load_observer(id, config):
    image_observers[id] = instantiate_class(
        config["class"],
        id,
        config,
        state_cursor=state.get_cursor(("video", "image_observers", id)),
    )


def load_video_config(config: dict):
    overlay.overlays = {}

    if "video" not in state:
        state["video"] = {
            "image_sources": {},
            "image_observers": {},
        }

    _rec_state.set_self(
        {
            "selected_sources": [],
            "is_recording": False,
            "write_dir": _config.media_dir,
            "filename_prefix": "",
        }
    )

    if "image_sources" in config:
        for src_id, conf in config["image_sources"].items():
            try:
                load_source(src_id, conf)
            except Exception:
                _log.exception(f"Exception while loading image source {src_id}:")

    if "image_observers" in config:
        for obs_id, conf in config["image_observers"].items():
            try:
                load_observer(obs_id, conf)
            except Exception:
                _log.exception(f"Exception while loading image observer {obs_id}:")


def load_video_writers():
    global video_writers
    video_writers = {}

    for src_id in image_sources.keys():
        video_writers[src_id] = video_write.VideoWriter(
            src_id + ".writer",
            {
                "src_id": src_id,
                "frame_rate": _config.video_record["video_frame_rate"],
                "queue_max_size": _config.video_record["max_write_queue_size"],
            },
            state_cursor=None,
        )


def update_video_config(config: dict):
    global image_sources, image_observers, video_config

    if len(image_sources) != 0:
        try:
            shutdown_video()
        except Exception:
            _log.exception("Exception while shutting down video:")

    image_sources = {}
    image_observers = {}

    load_video_config(config)
    load_video_writers()

    start()

    _log.info(f"Saving video config to '{_config.video_config_path.resolve()}'...")

    with open(_config.video_config_path, "w") as f:
        json.dump(config, f, indent=4)

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

    if has_trigger():
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

    for src in selected_sources:
        img, ts = src.get_image()
        p = video_write.save_image(img, ts, src.id)
        _log.info(f"Saved image from image_source '{src.id}' in {p}")


def _find_image_classes():
    global source_classes, source_params, observer_classes

    src_mods = load_modules(Path("./image_sources"), _log)
    obs_mods = load_modules(Path("./image_observers"), _log)

    def cls2str(name_cls):
        return mod.__name__ + "." + name_cls[1].__name__

    for mod, spec in src_mods.values():
        clss = find_subclasses(mod, ImageSource)
        cls_names = list(map(cls2str, clss))

        source_classes += cls_names
        for name, (_, cls) in zip(cls_names, clss):
            image_class_params[name] = cls.default_params

    for mod, spec in obs_mods.values():
        clss = find_subclasses(mod, ImageObserver)
        cls_names = list(map(cls2str, clss))
        observer_classes += cls_names
        for name, (_, cls) in zip(cls_names, clss):
            image_class_params[name] = cls.default_params


def init(log, config):
    global _log, _config, video_config, _rec_state
    _log = log
    _config = config
    config_path = config.video_config_path

    _find_image_classes()

    _rec_state = state.get_cursor(("video", "record"))

    if not config_path.exists():
        video_config = {
            "image_sources": {},
            "image_observers": {},
        }

        try:
            with open(config_path, "w") as f:
                json.dump(video_config, f, indent=4)
        except Exception:
            log.exception(f"Exception while writing to {str(config_path)}")
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

    _log.info(
        f"Starting {len(image_observers)} image observers: {', '.join(list(image_observers.keys()))}"
    )
    for img_obs in image_observers.values():
        img_obs.start()

    _log.info(
        f"Starting {len(image_sources)} image sources: {', '.join(list(image_sources.keys()))}"
    )
    for src_id, img_src in image_sources.items():
        img_src.start()
        update_acquire_callback(src_id)


def shutdown_video():
    for w in video_writers.values():
        try:
            w.stop_observing()
            w.shutdown()
            w.join()
        except Exception:
            _log.exception("Error while closing video writers:")

    for obs in image_observers.values():
        try:
            obs.stop_observing()
            obs.shutdown()
            obs.join()
        except Exception:
            _log.exception("Error while closing image observers:")

    if has_trigger():
        start_trigger(update_state=False)

    for img_src in image_sources.values():
        try:
            img_src.stop_event.set()
            img_src.join()
        except Exception:
            _log.exception("Error while closing image sources:")

    for src_id in image_sources.keys():
        state.remove_callback(("video", "image_sources", src_id, "acquiring"))

    state.delete("video")
    image_sources.clear()
    image_observers.clear()

    if has_trigger():
        stop_trigger(update_state=False)


def shutdown():
    shutdown_video()
