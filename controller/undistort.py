"""
This module is responsible for correcting the distortion of the camera lens using existing functions from Open-CV.
As the camera is located close to the target, and captures a relatively wide angle frame, the barrel distortion is
significant. The function get_distortion_matrix analyzes images that contain a checkerboard, and produces the
required undistortion matrix and coefficients. These values are constant for a specific camera and lens combination.
The function get_undistort_mapping computes from these parameters the required transformations, to be used with images,
single points of data, or data arrays.
"""

import numpy as np
import cv2 as cv
from pathlib import Path
from tqdm.auto import tqdm

# Undistortion code from:
#   https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_calib3d/py_calibration/py_calibration.html

# Static un-distortion matrices for the cameras.
flir_firefly_attr = {
    "mtx": np.array(
        [
            [1.14515564e03, 0.00000000e00, 7.09060713e02],
            [0.00000000e00, 1.14481967e03, 5.28220061e02],
            [0.00000000e00, 0.00000000e00, 1.00000000e00],
        ]
    ),
    "dist": np.array(
        [
            [
                -4.25580120e-01,
                3.02361751e-01,
                -1.56952670e-03,
                -4.04385846e-04,
                -2.27525587e-01,
            ]
        ]
    ),
}

flir_blackfly_attr = {
    "dist": np.array(
        [
            [
                -3.73487649e-01,
                1.70639650e-01,
                2.12535002e-04,
                9.02337277e-05,
                -4.25039396e-02,
            ]
        ]
    ),
    "mtx": np.array(
        [
            [1.04345883e03, 0.00000000e00, 7.94892178e02],
            [0.00000000e00, 1.04346538e03, 6.09748241e02],
            [0.00000000e00, 0.00000000e00, 1.00000000e00],
        ]
    ),
}


class CalibrationException(Exception):
    pass


def get_distortion_matrix(chkr_im_path: Path, rows=6, cols=9):
    """
    Finds the undistortion matrix of the lens based on multiple images
    with checkerboard. It's possible to implement this function using Aruco markers as well.

    :param: chkr_im_path - path to folder with images with checkerboards
    :param: rows - number of rows in checkerboard
    :param: cols - number of cols in checkerboard
    :return: numpy array: camera matrix, numpy array: distortion coefficients
    """

    # termination criteria
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    objp = np.zeros((rows * cols, 3), np.float32)
    objp[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2)

    # Arrays to store object points and image points from all the images.
    objpoints = []  # 3d point in real world space
    imgpoints = []  # 2d points in image plane.

    image_paths = list(chkr_im_path.iterdir())

    # drawings = []
    # imgs = []
    for fname in tqdm(image_paths):
        img = cv.imread(str(fname))
        if img is None:
            raise CalibrationException(f"Can't read image at {fname}")
        shape = img.shape
        # imgs.append(img)
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

        # Find the chess board corners
        ret, corners = cv.findChessboardCorners(gray, (cols, rows), None)

        # If found, add object points, image points (after refining them)
        if ret is True:
            objpoints.append(objp)

            corners2 = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            imgpoints.append(corners2)

            # Draw and display the corners
            # img = cv.drawChessboardCorners(img, (cols,rows), corners2,ret)
            # drawings.append(img)

    ret, mtx, dist, rvecs, tvecs = cv.calibrateCamera(
        objpoints, imgpoints, shape[::-1][1:], None, None
    )

    if not ret:
        raise CalibrationException("Error finding distortion matrix")

    return {"mtx": mtx, "dist": dist}


def get_undistort_mapping(width, height, cam_attr, alpha=0):
    """
    Computes the undistortion mapping for the given mtx and dist matrices.

    :param width: int, width of the image
    :param height: int, height of the image
    :param cam_attr: A dictionary with "mtx" and "dist" keys for a specific camera and lens.
    :param dist: numpy array, distortion coefficients
    :param alpha: float in the range (0,1)
    :return:
        mapx, mapy - numpy arrays, x,y coordinates for each image coordinate for undistorting an image.
        roi - tuple, (x, y, w, h) region of interest tuple
        newcameramtx - numpy array,  camera matrix for undistorting points in the specific (width, height) frame.
    """
    newcameramtx, roi = cv.getOptimalNewCameraMatrix(
        cam_attr["mtx"], cam_attr["dist"], (width, height), alpha, (width, height)
    )
    return (
        cv.initUndistortRectifyMap(
            cam_attr["mtx"], cam_attr["dist"], None, newcameramtx, (width, height), 5
        ),
        roi,
        newcameramtx,
    )


def undistort_image(img, mapping, roi=None):
    """
    When roi is not None the image is cropped to the ROI.
    :param img: numpy array: image to undistort
    :param mapping: a tuple (mapx, mapy)
    :return: numpy array: undistorted version of img according to the mapping
    """
    mapx, mapy = mapping

    dst = cv.remap(img, mapx, mapy, cv.INTER_LINEAR)

    # crop the image
    if roi:
        x, y, w, h = roi
        dst = dst[y : y + h, x : x + w]

    return dst


def undistort_point(p, newcameramtx, cam_attr):
    """
    :param p: iterable, coordinate to undistort
    :param newcameramtx: numpy array, camera matrix for the specific (width, height) frame.
    :param cam_attr: A dictionary with "mtx" and "dist" keys for a specific camera and lens.
    :return: numpy array, undistorted points
    """

    p = np.array(p)
    if np.any(np.isnan(p)):
        return np.nan, np.nan

    return cv.undistortPoints(
        np.expand_dims(p, axis=0), newcameramtx, cam_attr["dist"]
    ).squeeze()


def undistort_data(
    data, width, height, cam_attr, cols=(("x1", "y1"), ("x2", "y2")), alpha=0
):
    """
    Undistorts a bulk of data. assumes location data in (cent_x, cent_y, x1, y1, x2, y2) format
    :param data: Pandas DataFrame, data to undistort
    :param width: int
    :param height: int
    :param cols: tuple of pairs of strings which are column names in the df
    :param cam_attr: A dictionary with "mtx" and "dist" keys for a specific camera and lens.
    :param alpha: float in (0,1)
    :return: pandas df, the undistorted data (deep copy of the original data)
    """

    # deep copy of the original data
    ret_df = data.copy()

    # get transformation for the specific frame
    _, _, newcameramtx = get_undistort_mapping(width, height, cam_attr, alpha=alpha)

    # for each pair of columns which constitute a coordinate, undistort
    for xy in cols:
        x = xy[0]
        y = xy[1]
        points = data[[x, y]].values
        undistorted = cv.undistortPoints(
            np.expand_dims(points, axis=0),
            newcameramtx,
            cam_attr["dist"],
            P=newcameramtx,
        )
        ret_df[[x, y]] = undistorted.squeeze(1)

    return ret_df
