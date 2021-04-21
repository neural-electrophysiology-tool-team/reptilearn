"""
This module is responsible for creating visualizations for images, videos, statistical plots and notebook widgets.
Documented more loosely than the other modules, as it's less important
"""

import os
import numpy as np
import cv2 as cv
import matplotlib.pyplot as plt
from tqdm.auto import tqdm
import matplotlib.patches as patches
from matplotlib.collections import LineCollection


from bbox import xyxy_to_centroid, nearest_bbox
import undistort


"""
-----------------------  Non Video functions ------------------------------
"""


def plot_image(detections, img, output_path=None, show_img=True):
    """
    :param detections: Numpy array, output detections of a bbox object detector
    :param img: Numpy array, bounding boxes are drawn on this image
    :param output_path: path to save the image, or None to not save.
    :param show_img: bool, whether to show the image or not
    :return:
    """

    plt.figure()
    fig, ax = plt.subplots(1, figsize=(12, 9))
    ax.imshow(img)

    if detections is not None:
        # browse detections and draw bounding boxes
        for x1, y1, box_w, box_h, conf in detections:
            color = (0, 0, 1, 1)
            bbox = patches.Rectangle(
                (x1, y1), box_w, box_h, linewidth=2, edgecolor=color, facecolor="none"
            )
            ax.add_patch(bbox)
            plt.text(
                x1,
                y1,
                s=str(round(conf, 2)),
                color="white",
                verticalalignment="top",
                bbox={"color": color, "pad": 0},
            )
    plt.axis("off")

    if output_path is not None:
        plt.savefig(output_path, bbox_inches="tight", pad_inches=0.0)

    if show_img:
        plt.show()
    else:
        plt.clf()


def draw_sequences(
    arr_X,
    arr_Y,
    arr_pred,
    ax,
    l_alpha=0.35,
    sctr_s=0.5,
    sctr_alpha=1,
    past_c="b",
    ftr_c="r",
    pred_c="g",
    diff_c="k",
    xlabel="past",
    ylabel="future",
    draw_diffs=True,
    tensor_func=lambda x: x[:, :, 2:],
):
    """
    Draw sequences as points with lines connecting them. Operates on a single sequence or a batch of sequences.
    Not recommended to draw more than a few thousands sequences or sequence pairs, possible to use other rasterized
    functions
    :param arr_X: 3D numpy array of X sequences
    :param arr_Y: 3D numpy array of Y sequences
    :param arr_pred: 3D numpy array of predictions
    :param ax: matplotlib ax to draw on
    :param l_alpha: float in [0,1], line alpha
    :param sctr_s: int, size of the scatter points
    :param sctr_alpha: float in [0,1], sactter alpha
    :param past_c: str (or other represntation of color), color of X sequences
    :param ftr_c: str, color of Y sequences
    :param pred_c: str, color of prediction sequences
    :param diff_c: str, color of line difference between ground truth and prediction sequences
    :param draw_diffs: bool, whether to draw the differences
    :param tensor_func: function to slice the 3D arrays with
    """
    if arr_X is not None:
        if len(arr_X.shape) == 2:
            arr_X = arr_X.reshape(1, arr_X.shape[0], arr_X.shape[1])
        arr_X = tensor_func(arr_X)
    if arr_Y is not None:
        if len(arr_Y.shape) == 2:
            arr_Y = arr_Y.reshape(1, arr_Y.shape[0], arr_Y.shape[1])
        arr_Y = tensor_func(arr_Y)
    if draw_diffs:
        if len(arr_pred.shape) == 2:
            arr_pred = arr_pred.reshape(1, arr_pred.shape[0], arr_pred.shape[1])
        arr_pred = tensor_func(arr_pred)

    if arr_X is not None:
        ax.add_collection(
            LineCollection(
                segments=[seq for seq in arr_X],
                colors=[past_c],
                label=xlabel,
                alpha=l_alpha,
            )
        )
        ax.scatter(
            arr_X[:, :, 0], arr_X[:, :, 1], s=sctr_s, color=past_c, alpha=sctr_alpha
        )
    if arr_Y is not None:
        ax.add_collection(
            LineCollection(
                segments=[seq for seq in arr_Y],
                colors=[ftr_c],
                label=ylabel,
                alpha=l_alpha,
            )
        )
        ax.scatter(
            arr_Y[:, :, 0], arr_Y[:, :, 1], s=sctr_s, color=ftr_c, alpha=sctr_alpha
        )
    if draw_diffs:
        ax.add_collection(
            LineCollection(
                segments=[seq for seq in arr_pred],
                colors=[pred_c],
                label="pred",
                alpha=l_alpha,
            )
        )
        diffs = [
            np.array([arr_pred[j, i], arr_Y[j, i]])
            for i in range(arr_pred.shape[1])
            for j in range(arr_pred.shape[0])
        ]
        ax.add_collection(
            LineCollection(segments=diffs, colors=[diff_c], label="diff", alpha=l_alpha)
        )
        ax.scatter(
            arr_pred[:, :, 0],
            arr_pred[:, :, 1],
            s=sctr_s,
            color=pred_c,
            alpha=sctr_alpha,
        )


"""
-------------------- Video closure functions ----------------------
Functions in this part follow a closure pattern. The functions return a function that's passed to the process_video
function. 
"""


def online_centroid_visualizer(detector, color, window_size):
    centroids = []

    def fn(orig_frame, write_frame, frame_counter):
        detections = detector.detect_image(orig_frame)
        if detections is not None:
            if len(centroids) > 0:
                detection = nearest_bbox(detections, centroids[-1])
            else:
                detection = detections[0]

            centroid = xyxy_to_centroid(detection)
            if len(centroids) >= window_size:
                centroids.pop(0)

            centroids.append(centroid)

        for c in centroids:
            if np.isnan(c[0]):
                continue

            x = int(c[0])
            y = int(c[1])
            cv.circle(
                write_frame,
                center=(x, y),
                radius=2,
                color=color,
                thickness=-1,
                lineType=cv.LINE_AA,
            )

    return fn


def missed_frames_saver(
    detector, output_dir, prefix="frame", save_thresh=0.8, above=False, draw_bbox=True
):
    """
    Save missed frames according to some threshold
    """
    saved_counter = 0

    if above:

        def save_func(detec, save_thres):
            return (detec is not None) and (detec[0][4] > save_thres)

    else:

        def save_func(detec, save_thres):
            return (detec is None) or (detec[0][4] < save_thres)

    try:
        os.makedirs(output_dir)
    except FileExistsError:
        pass

    def fn(orig_frame, write_frame, frame_counter):
        nonlocal saved_counter

        detections = detector.detect_image(orig_frame)

        if save_func(detections, save_thresh):
            if detections is not None:
                prob = str(round(detections[0][4], 3))
            else:
                prob = "0"

            save_path = os.path.join(
                output_dir, prefix + "_" + prob + "_" + str(saved_counter) + ".jpg"
            )

            if draw_bbox:
                plot_image(
                    detections, orig_frame, output_path=save_path, show_plot=False
                )
            else:
                cv.imwrite(save_path, orig_frame)

            saved_counter += 1

    return fn


def video_sampler(output_path, freq, f_name):
    """
    Save arbitrary frames at constant frequency from video to path
    """

    if not os.path.exists(output_path):
        os.mkdir(output_path)

    def fn(orig_frame, write_frame, frame_counter):
        if frame_counter % freq == 0:
            fname = os.path.join(output_path, f_name + str(frame_counter) + ".jpg")
            cv.imwrite(fname, orig_frame)

    return fn


def is_point_in_bounds(p, frame):
    px, py = p
    return px >= 0 and px < frame.shape[1] and py >= 0 and py < frame.shape[0]


def offline_bbox_visualizer(
    bboxes, color=(0, 0, 255), window_size=20, line_thickness=1
):
    """
    Return a visualize function that draws a number of last bboxes on each frame according to
    the bboxes array.

    :param bboxes: Numpy array containing bboxes for each frame
    :param color: Bbox color as a BGR tuple
    :param window_size: Number of previous bboxes that will be drawn to the frame
    :param line_thickness: Bbox rectangle line thickness
    """

    def fn(orig_frame, write_frame, frame_counter):
        for i in range(window_size):
            idx = max(frame_counter - i, 0)
            bbox = bboxes[idx]
            if not np.isnan(bbox[0]):
                bbox = bbox * (bbox > 0)  # zero out negative coords.
                bbox = bbox.astype(int)
                cv.rectangle(
                    write_frame, tuple(bbox[:2]), tuple(bbox[2:]), color, line_thickness
                )

    return fn


def offline_centroid_visualizer(
    bboxes, color=(255, 0, 0), window_size=20, dot_radius=4
):
    """
    Return a visualize function that draws a number of last bbox centroids on each frame
    according to the bboxes array.

    :param bboxes: Numpy array containing bboxes for each frame
    :param color: Centroid color as a BGR tuple
    :param window_size: Number of previous centroids that will be drawn to the frame
    :param dot_radius: Radius of the centroid dot
    """

    def fn(orig_frame, write_frame, frame_counter):
        for i in range(window_size):
            idx = max(frame_counter - i, 0)
            bbox = bboxes[idx]
            if not np.isnan(bbox[0]):
                c = xyxy_to_centroid(bbox).astype(int)
                if is_point_in_bounds(c, write_frame):
                    cv.circle(
                        write_frame,
                        center=tuple(c),
                        radius=dot_radius,
                        color=color,
                        thickness=-1,
                        lineType=cv.LINE_AA,
                    )

    return fn


def draw_trajectory(
    write_frame,
    traj_bboxes,
    draw_lines=True,
    dot_radius=4,
    color=(255, 0, 0),
    line_thickness=1,
):
    """
    Draws a trajectory of the center bottom edge points in the traj_bboxes array.
    
    :param write_frame: Video frame array to draw to
    :param traj_bboxes: Numpy array of trajectory bboxes
    :param draw_lines: Whether to draw lines between consecutive trajectory points
    :param dot_radius: Radius of trajectory points
    :param color: Trajectory color as a BGR tuple
    :param line_thickness: Trajectory lines thickness
    """
    prev_point = None

    for bbox in traj_bboxes:
        if np.isnan(bbox[0]):
            continue

        c = xyxy_to_centroid(bbox).astype(int)
        p = (c[0], int(bbox[3]))
        if is_point_in_bounds(p, write_frame):
            cv.circle(
                write_frame,
                center=p,
                radius=dot_radius,
                color=color,
                thickness=-1,
                lineType=cv.LINE_AA,
            )

        if draw_lines and prev_point is not None:
            cv.line(
                write_frame, prev_point, p, color, thickness=line_thickness,
            )
        prev_point = p


def offline_trajectory_visualizer(
    bboxes,
    past_length,
    future_length,
    past_color=(255, 0, 0),
    future_color=(0, 0, 255),
    draw_lines=True,
    dot_radius=4,
    line_thickness=1,
):
    """
    Return a visualize function that draws the past and future trajectory of the supplied bboxes.

    :param bboxes: Numpy array of bboxes
    :param past_length: Number of time steps to draw from the past trajectory
    :param future_length: Number of time steps to draw from the future trajectory
    :param past_color: Color of past trajectory as BGR tuple
    :param future_color: Color of future trajectory as BRG tuple
    :param draw_lines: Whether to draw lines between consecutive trajectory points
    :param dot_radius: Radius of trajectory points
    :param line_thickness: Thickness of trajectory lines
    """

    def fn(orig_frame, write_frame, frame_counter):
        if frame_counter - past_length - 1 >= 0:
            past = bboxes[frame_counter - past_length - 1 : frame_counter - 1]
            draw_trajectory(
                write_frame, past, draw_lines, dot_radius, past_color, line_thickness,
            )

        if frame_counter + future_length - 1 < bboxes.shape[0]:
            future = bboxes[frame_counter - 1 : frame_counter + future_length - 1]
            draw_trajectory(
                write_frame,
                future,
                draw_lines,
                dot_radius,
                future_color,
                line_thickness,
            )

    return fn


def offline_touch_visualizer(
    touches,
    hits,
    touch_xs,
    hit_color=(0, 255, 0),
    touch_color=(0, 0, 255),
    touch_pos_color=(255, 0, 255),
    touch_radius=16,
    max_alpha=0.5,
    duration=30,
):
    last_touch = None
    last_touch_x = None
    is_hit = False

    def fn(orig_frame, write_frame, frame_counter):
        nonlocal last_touch, is_hit, last_touch_x

        if touches[frame_counter]:
            last_touch = frame_counter
            is_hit = hits[frame_counter]
            last_touch_x = int(touch_xs[frame_counter])

        if last_touch is not None:
            cur_duration = frame_counter - last_touch
            if cur_duration > duration:
                last_touch = None
                last_touch_x = None
                is_hit = False
                return

            alpha = max_alpha * (1 - cur_duration / duration)
            color = hit_color if is_hit else touch_color
            overlay = write_frame.copy()
            cv.rectangle(
                overlay, (0, 0), (overlay.shape[1], overlay.shape[0]), color, -1
            )

            cv.addWeighted(overlay, alpha, write_frame, 1 - alpha, 0, write_frame)

            if touch_xs is not None and last_touch_x is not None:
                tx = last_touch_x
                cv.rectangle(
                    write_frame,
                    (tx - touch_radius, 0),
                    (tx + touch_radius, 2 * touch_radius),
                    touch_pos_color,
                    -1,
                )

    return fn


def offline_bug_visualizer(bug_x, color=(255, 0, 0), radius=16):
    def fn(orig_frame, write_frame, frame_counter):
        x = bug_x[frame_counter]
        if not np.isnan(x):
            x = int(x)
            cv.rectangle(
                write_frame, (x - radius, 0), (x + radius, 2 * radius), color, -1
            )

    return fn


def visualize_prediction(
    predictor,
    write_frame,
    forecast,
    hit_x,
    hit_steps,
    draw_forecast_bbox=False,
    draw_pred_lines=True,
    prediction_color=(0, 255, 0),
    hit_color=(0, 0, 255),
    bbox_color=(255, 255, 0),
    dot_radius=4,
    line_thickness=1,
):
    """
    Draw a predictor prediction on a frame
    """
    if forecast is not None:
        draw_trajectory(
            write_frame,
            forecast,
            draw_pred_lines,
            dot_radius,
            prediction_color,
            line_thickness,
        )

        if draw_forecast_bbox:
            for bbox in forecast:
                if np.isnan(bbox[0]):
                    continue

                bbox = bbox * (bbox > 0)  # zero out negative coords.
                cv.rectangle(
                    write_frame,
                    tuple(bbox[:2]),
                    tuple(bbox[2:]),
                    bbox_color,
                    line_thickness,
                )

    if hit_x is not None:
        hp = (int(hit_x), predictor.prediction_y_threshold)

        if is_point_in_bounds(hp, write_frame):
            cv.circle(
                write_frame,
                center=hp,
                radius=dot_radius * 4,
                color=hit_color,
                thickness=-1,
                lineType=cv.LINE_AA,
            )

            cv.putText(
                write_frame,
                str(hit_steps),
                (hp[0], hp[1] - 20),
                cv.FONT_HERSHEY_COMPLEX,
                fontScale=0.4,
                color=(255, 0, 0),
                thickness=1,
                lineType=cv.LINE_AA,
            )


def offline_predictor_visualizer(predictor, bboxes, **visualize_prediction_args):
    """
    Return a visualize function that draws a predictor's forecast on each frame.

    :param predictor: HitPredictor object that is used to generate forecasts
    :param bboxes: Numpy array of bboxes per frame
    :param visualize_prediction_args: Additional arguments that will be passed to visualize_prediction().
    """

    def fn(orig_frame, write_frame, frame_counter):
        forecast, hit_point, hit_steps = predictor.handle_detection(
            bboxes[frame_counter]
        )
        visualize_prediction(
            predictor,
            write_frame,
            forecast,
            hit_point,
            hit_steps,
            **visualize_prediction_args,
        )

    return fn


def predictor_visualizer(predictor, show_forecast_bbox=False):
    def fn(orig_frame, write_frame, frame_counter):
        forecast, hit_point, hit_steps = predictor.handle_frame(orig_frame)
        visualize_prediction(
            predictor, write_frame, forecast, hit_point, hit_steps, show_forecast_bbox
        )

    return fn


def get_correction_fn(homography, screen_x_res, cam_attr):  # 1920
    """
    Receive the parameters to conduct the lense correction and coordinate transformation
    on the write_frame image.

    :param aff_mat: affine transformation to touch screen coordinates
    :param screen_x_res: screen resolution
    :param cam_attr: A dictionary with "mtx" and "dist" keys for a specific camera and lens.
    :return:
    """

    first_frame = True
    #  compute the distortion mapping once, according to (w, h)
    mapx, mapy, roi = None, None, None

    def fn(frame):
        nonlocal mapx, mapy, roi, first_frame
        if first_frame:
            first_frame = False
            frame_height, frame_width = frame.shape[0], frame.shape[1]
            (mapx, mapy), roi, _ = undistort.get_undistort_mapping(
                frame_width, frame_height, cam_attr
            )

        # write over write frame and use the corrected
        write_frame = undistort.undistort_image(frame, (mapx, mapy))
        #if homography is not None:
        #    write_frame = calib.transform_image(write_frame, homography, screen_x_res)
        return write_frame

    return fn


def process_video(
    video_path,
    output_path,
    process_fns,
    correction_fn=None,
    start_frame=0,
    num_frames=None,
    frame_rate=None,
    resize_to_width=None,
):
    """
    Open a video file, run all functions in process_fns, and write the
    processed video to file.

    Each function in process_fns has the following signature:

    fn(orig_frame, write_frame, frame_counter)

    orig_frame - the original video frame.
    write_frame - the frame that will be written to file.
    frame_counter - current frame number.

    correction_fn has the following signature:
    fn(input_frame) -> output_frame
    output_frame is the transformed frame.

    :param video_path: path of original video
    :param output_path: path of processed video or None if writing is not necessary.
    :param process_fns: a list of process functions
    :param correction_fn: a function responsible for undistorting and transforming the image
    :param start_frame: the first frame to be processed.
    :param num_frames: number of frames to process or None to process the whole video.
    :param frame_rate: the framerate of the processed video or None to use the original framerate.
    :param resize_to_width: when not None, the output is resized after processing each frame.
    """
    vcap = cv.VideoCapture(str(video_path))

    if start_frame != 0:
        vcap.set(cv.CAP_PROP_POS_FRAMES, start_frame)

    if num_frames is None:
        num_frames = int(vcap.get(cv.CAP_PROP_FRAME_COUNT)) - start_frame

    if frame_rate is None:
        frame_rate = vcap.get(cv.CAP_PROP_FPS)

    for frame_counter in tqdm(range(start_frame, start_frame + num_frames)):
        ret, orig_frame = vcap.read()

        if not ret:
            print("error reading frame")
            break

        if correction_fn is not None:
            orig_frame = correction_fn(orig_frame)

        write_frame = orig_frame.copy()

        if output_path is not None and frame_counter == start_frame:
            if resize_to_width is not None:
                rwidth = resize_to_width
                rheight = int(
                    write_frame.shape[0] * resize_to_width / write_frame.shape[1]
                )
            else:
                rwidth = write_frame.shape[1]
                rheight = write_frame.shape[0]

            videowriter = cv.VideoWriter(
                str(output_path),
                cv.VideoWriter_fourcc(*"mp4v"),
                frame_rate,
                (rwidth, rheight),
            )

        # process the frame with each function in the list
        for fn in process_fns:
            fn(orig_frame, write_frame, frame_counter)

        if output_path is not None:
            if resize_to_width is not None:
                write_frame = cv.resize(write_frame, (rwidth, rheight))

            videowriter.write(write_frame)

    vcap.release()

    if output_path is not None and videowriter:
        videowriter.release()


def get_vid_frames(vid_path, start, num, correction_fn=None):
    """
    Return a consecutive list of frames from a video file.

    :param vid_path: Path of the video file.
    :param start: The first frame to retrieve.
    :param num: The number of frames to retrieve.
    :param correction_fn: A lens and homography correction function to apply to each frame.
    """
    vcap = cv.VideoCapture(str(vid_path))
    vcap.set(cv.CAP_PROP_POS_FRAMES, start)
    frames = []
    for i in range(num):
        ret, frame = vcap.read()
        if correction_fn:
            frame = correction_fn(frame)
        frames.append(frame)

    return frames


def gen_trial_video(
    trial,
    df,
    start_frame=0,
    end_frame=None,
    past_color=(255, 0, 0),
    future_color=(0, 0, 255),
    dot_radius=4,
    line_thickness=2,
    video_width=1280,
    out_dir="../labelled",
    out_path_prefix="data",
):
    """ Convenience function to generate videos by trial name """
    vid_path = dataset.get_trial_video_path(trial)
    out_path = os.path.join(out_dir, f'{trial.replace("/", "_")}_{out_path_prefix}.mp4')
    homography, _ = dataset.find_last_homography(dataset.get_trial_path(trial).parent)
    correction_fn = get_correction_fn(homography, 1920)
    tdf = df.loc[trial]

    bboxes = tdf[["x1", "y1", "x2", "y2"]].values
    hits = tdf["is_hit"]
    touches = tdf["is_touch"]
    touch_xs = tdf["touch_x"]
    bug_x = tdf["bug_x"]

    num_frames = end_frame - start_frame if end_frame is not None else None

    process_video(
        video_path=vid_path,
        output_path=out_path,
        process_fns=(
            [
                offline_bug_visualizer(bug_x),
                offline_touch_visualizer(touches, hits, touch_xs),
                offline_trajectory_visualizer(
                    bboxes,
                    past_color=past_color,
                    future_color=future_color,
                    dot_radius=dot_radius,
                    past_length=20,
                    future_length=20,
                ),
                offline_bbox_visualizer(
                    bboxes,
                    color=(0, 0, 0),
                    line_thickness=line_thickness,
                    window_size=1,
                ),
                offline_centroid_visualizer(
                    bboxes, color=(0, 0, 0), dot_radius=dot_radius * 2, window_size=1
                ),
            ]
        ),
        correction_fn=correction_fn,
        start_frame=start_frame,
        num_frames=num_frames,
        resize_to_width=video_width,
    )
