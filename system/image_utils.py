import io
from PIL import Image


def resize_image(img: Image, size=(None, None)):
    """
    Resize an image to the desired size.

    :param img: The image as a numpy array.
    :param size: A (width, height) tuple.

    When both width and height are None, a copy of the original image is returned.
    When one of the size parameters is None, the returned image will retain the aspect
    ratio of the original image.
    """
    if (size[0] is None and size[1] is None) or (
        size[0] == img.size[0] and size[1] == img.size[1]
    ):
        return img.copy()

    elif size[0] is None or size[1] is None:
        ratio = img.size[0] / img.size[1]

        if size[0] is None:
            if size[1] == img.size[1]:
                return img.copy()
            else:
                size = (int(size[1] * ratio), size[1])

        elif size[1] is None:
            if size[0] == img.size[0]:
                return img.copy()
            else:
                size = (size[0], int(size[0] / ratio))

    return img.resize((int(size[0]), int(size[1])), resample=Image.BOX)


def encode_image(img, encoding="WebP", encode_params={}, shape=(None, None)):
    """
    Encode the supplied image using the Pillow library, possibly resizing it first.
    For possible encodings and encoding parameters see: https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html

    :param img: A numpy array containing image data.
    :param encoding: A string with the desired encoding (see Pillow docs)
    :param encode_params: A dict with encoding paramaeters (see Pillow docs)
    :param shape: The desired shape passed to resize_image (see above)

    Return the encoded image as a byte string.
    """
    im = resize_image(Image.fromarray(img), shape)
    with io.BytesIO() as output:
        im.save(output, format=encoding, **encode_params)
        return output.getvalue()
