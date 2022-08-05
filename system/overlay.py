import video_system

# TODO:
# - way to choose overlays

overlays = {}


def is_point_in_bounds(p, frame):
    px, py = p
    return px >= 0 and px < frame.shape[1] and py >= 0 and py < frame.shape[0]


class ImageOverlay:
    def apply(self, img, timestamp):
        return img


class ConfigurableOverlay(ImageOverlay):
    default_params = {"class": None}

    def __init__(self, config) -> None:
        self.config = config

    def get_config(self, key):
        if key in self.config:
            return self.config[key]
        elif key in self.__class__.default_params:
            return self.__class__.default_params[key]
        else:
            raise KeyError(f"Unknown config key: {key}")


class ObserverOverlay(ConfigurableOverlay):
    default_params = {
        **ConfigurableOverlay.default_params,
        "obs_id": None,
    }

    def apply(self, img, img_timestamp):
        obs_out, obs_out_timestamp = video_system.image_observers[
            self.get_config("obs_id")
        ].get_output()
        return self.obs_apply(img, img_timestamp, obs_out, obs_out_timestamp)

    def obs_apply(self, img, img_timestamp, obs_out, obs_out_timestamp):
        return img


def apply_overlays(img, timestamp, src_id):
    img = img.copy()
    if src_id in overlays:
        for overlay in overlays[src_id]:
            img = overlay.apply(img, timestamp)
    return img
