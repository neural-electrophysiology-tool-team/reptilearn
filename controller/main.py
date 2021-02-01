import api
from video_stream import VideoImageSource, VideoWriter
import multiprocessing as mp
import logging
from pathlib import Path


def main():
    logger = mp.log_to_stderr(logging.INFO)

    video_path = Path("./feeding4_vid.avi")
    vs = VideoImageSource(
        video_path, fps=60, repeat=True, start_frame=1000, end_frame=None
    )
    video_writer_conn1, video_writer_conn2 = mp.Pipe()
    flask_api = api.API([vs], [video_writer_conn1], {"stream_fps": 15})
    writer = VideoWriter(vs, video_writer_conn2, fps=60)

    writer.start()
    logger.info("Starting video source")
    vs.start()
    flask_api.run()
    vs.join()
    writer.join()
    flask_api.terminate()


if __name__ == "__main__":
    main()
