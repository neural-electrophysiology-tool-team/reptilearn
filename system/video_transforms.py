import numpy as np
from typing import Callable
import cv2
import random
from functools import reduce


# TODO
# - write transforms:
#   - start with simple test - dumb transform hardcoded
#   - yolo (much later): needs to listen for the pipe somehow
# - collect transforms: how? who collects?
#   - routes for transforms list, load transforms like tasks
# - run transform_image at select locations (start with stream_gen or encode_image_for_response)


def circle_transform(radius=4, color=(0, 255, 0)):
    def transform(out_img, img):
        center = random.randint(0, out_img.shape[1]), random.randint(
            0, out_img.shape[0]
        )
        cv2.circle(out_img, center, radius, color, thickness=5)
        return out_img

    return transform


def g2c_transform():
    def transform(out_img, img):
        if len(img.shape) == 3:
            return img
        else:
            return np.stack((img,) * 3, axis=-1)

    return transform


transforms = [g2c_transform()] + [
    circle_transform(
        random.randint(0, 100),
        (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)),
    )
    for _ in range(10)
]


def transform_image(img: np.array, transforms: [Callable] = []):
    return reduce(lambda acc, tr: tr(acc, img), transforms, img.copy())
