import cv2


def resize_image(img, size=(None, None)):
    """
    Resize an image to the desired size.

    :param img: The image as a numpy array.
    :param size: A (width, height) tuple.

    When both width and height are None, a copy of the original image is returned.
    When one of the size parameters is None, the returned image will retain the aspect
    ratio of the original image.
    """
    if (size[0] is None and size[1] is None) or (
        size[0] == img.shape[1] and size[1] == img.shape[0]
    ):
        return img.copy()

    elif size[0] is None or size[1] is None:
        ratio = img.shape[1] / img.shape[0]

        if size[0] is None:
            if size[1] == img.shape[0]:
                return img.copy()
            else:
                size = (int(size[1] * ratio), size[1])

        elif size[1] is None:
            if size[0] == img.shape[1]:
                return img.copy()
            else:
                size = (size[0], int(size[0] / ratio))

    return cv2.resize(img, size)


def encode_image(img, encoding=".jpg", encode_params=[], shape=(None, None)):
    """
    Encode the supplied image, possibly resizing it first.

    :param img: A numpy array containing image data.
    :param encoding: A string with the desired encoding (see OpenCV imencode docs)
    :param encode_params: OpenCV encode parameters (see OpenCV documentation)
    :param shape: The desired shape passed to resize_image (see above)

    Return the encoded image as a byte string.
    """
    resized_img = resize_image(img, shape)
    ret, img_buf_arr = cv2.imencode(".jpg", resized_img, encode_params)
    return img_buf_arr.tobytes()
