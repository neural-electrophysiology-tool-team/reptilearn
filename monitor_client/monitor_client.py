"""
Opens a gui (tkinter) on fullscreen to control the monitor placed in the arena,
Random colors from the colors list can be presented, specific colors or images/videos
given their path.

Author: Or Pardilov, 2021
Author: Tal Eisenberg

Starts a listening thread for MQTT messages which adds messages to a queue, 
the main thread executes them and maintains the gui.
"""

# TODO:
# - possibly move frame acquisition to queue

import tkinter
from PIL import ImageTk, Image
import json
import paho.mqtt.client as mqtt
import queue
import os
import random
import config
import imageio
import logging
import sys
import time
import threading

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(levelname)s] - %(asctime)s: %(message)s",
)

log = logging.getLogger("Monitor")

ENCODING = "utf-8"

# loading colors list
COLORS = []
with open("color_lst.txt", "r") as cfile:
    for line in cfile:
        COLORS.append(line.strip())


def on_connect(client, userdata, flags, rc):
    log.info(f"Connected to mqtt broker with result code {rc}")


def on_disconnect(client, userdata, rc):
    log.info(f"Disconnected from mqtt broker with result code {rc}")


def on_message(client, userdata, message):
    payload = str(message.payload.decode(ENCODING))
    msg = f"Message received topic={message.topic}"
    if payload is not None and len(payload) > 0:
        msg += f" payload={payload}"
    log.info(msg)

    # messages are added to a queue to avoid messages drop
    fs.tasks_q.put((message.topic, payload))


class FsWindow:
    """FsWindow class wraps the GUI data and variables"""

    def __init__(self):
        self.color = "black"

        self.tki = tkinter.Tk()
        # starts GUI on fullscreen
        self.tki.attributes("-fullscreen", True)
        self.size = (self.tki.winfo_screenwidth(), self.tki.winfo_screenheight())
        self.panel = tkinter.Canvas(self.tki)
        self.panel.configure(bg=self.color, width=self.size[0], height=self.size[1])
        self.panel.pack()

        self.tki.bind("<Escape>", self.exit_fs)
        self.tki.bind("<F>", self.enter_fs)

        self.vid_reader = None
        self.vid_loop = False
        self.vid_stop = False

        self.tasks_q = queue.Queue()

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = on_connect
        self.mqtt_client.on_disconnect = on_disconnect
        self.mqtt_client.connect(config.mqtt["host"], config.mqtt["port"])
        self.mqtt_client.on_message = on_message
        self.mqtt_client.subscribe("monitor/image")
        self.mqtt_client.subscribe("monitor/play_video")
        self.mqtt_client.subscribe("monitor/stop_video")
        self.mqtt_client.subscribe("monitor/color")
        self.mqtt_client.subscribe("monitor/clear")
        self.mqtt_client.loop_start()

    def update_size(self):
        self.size = (self.tki.winfo_screenwidth(), self.tki.winfo_screenheight())

    def enter_fs(self, event=None):
        self.tki.attributes("-fullscreen", True)

    def exit_fs(self, event=None):
        self.tki.attributes("-fullscreen", False)

    def clear(self):
        self.panel.delete(self.image_on_canvas)
        self.image_on_canvas = None
        self.load_color()

    def load_img(self, im_path):
        # loads image from a given path to screen
        pil_image, x = self.resize_image(Image.open(im_path))
        imgtk = ImageTk.PhotoImage(pil_image)
        self.panel.imgtk = imgtk
        self.image_on_canvas = self.panel.create_image(
            x, 0, image=imgtk, anchor=tkinter.NW
        )

    def load_video(self, vid_path):
        # starts the presentation of a video
        self.update_size()
        self.vid_reader = imageio.get_reader(vid_path, "ffmpeg")
        video_meta = self.vid_reader.get_meta_data()
        self.vid_fps = video_meta["fps"]
        self.vid_length = self.vid_reader.count_frames()
        self.vid_frame_dur = 1 / self.vid_fps
        self.vid_stop = False
        self.vid_timestamps = []
        self.prev_frame = None
        self.play_start_time = time.time()
        self.image_on_canvas = None
        log.info(f"Playing video {vid_path} @ {self.vid_fps}fps")
        self.player_loop()

    def resize_image(self, pil_image):
        width, height = pil_image.size
        w, h = self.size
        if width == w and height == h:
            return pil_image, 0

        ratio = min(w / width, h / height)
        width = int(width * ratio)
        height = int(height * ratio)
        x_center = (w - width) // 2
        return pil_image.resize((width, height), Image.ANTIALIAS), x_center

    def player_loop(self):
        if self.vid_stop:
            self.on_video_end()
            return

        try:
            frame_time = time.time() - self.play_start_time
            cur_frame = int(frame_time // self.vid_frame_dur)
            frame_start_time = cur_frame * self.vid_frame_dur

            if self.prev_frame is None or self.prev_frame != cur_frame:
                image = self.vid_reader.get_data(cur_frame)
                pil_image, x = self.resize_image(Image.fromarray(image))

                imgtk = ImageTk.PhotoImage(pil_image)

                if self.image_on_canvas is None:
                    self.image_on_canvas = self.panel.create_image(
                        x, 0, image=imgtk, anchor=tkinter.NW
                    )
                    self.panel.image = imgtk
                else:
                    self.panel.itemconfig(self.image_on_canvas, image=imgtk)
                    self.panel.image = imgtk

                self.tki.update_idletasks()
                ts = time.time()
                self.vid_timestamps.append((cur_frame, ts))
                self.prev_frame = cur_frame

            delay = int((self.vid_frame_dur - frame_start_time) // 1000)
            self.tki.after(delay, self.player_loop)

        except IndexError:
            if self.vid_loop:
                log.info("Replaying video")
                self.tki.after(self.vid_frame_dur, self.player_loop)
            else:
                self.on_video_end()

    def on_video_end(self):
        log.info("Finished playing video.")
        self.vid_stop = False
        self.vid_loop = False
        self.vid_reader.close()
        self.mqtt_client.publish(
            "monitor/playback_ended", json.dumps(self.vid_timestamps)
        )
        self.clear()

    def update_g(self):
        while True:
            msg = self.tasks_q.get()
            if msg is None:
                break
            topic = msg[0]
            payload = msg[1]
            if topic == "monitor/image":
                if os.path.exists(payload):
                    self.load_img(payload)
                else:
                    log.error(f"The image in {payload} was not found.")

            elif topic == "monitor/play_video":
                if os.path.exists(payload):
                    self.load_video(payload)
                else:
                    log.error(f"The image in {payload} was not found.")

            elif topic == "monitor/stop_video":
                self.vid_stop = True

            elif topic == "monitor/color":
                self.set_color(payload)

            elif topic == "monitor/clear":
                self.clear()

    def set_color(self, color):
        if color == "random":
            color = random.choice(COLORS)

        if color != self.color:
            self.color = color
            self.load_color()

    def load_color(self):
        self.panel.configure(bg=self.color)


if __name__ == "__main__":
    fs = FsWindow()
    t = threading.Thread(target=fs.update_g)
    t.start()
    fs.tki.mainloop()
    log.info("Shutting down...")
    fs.tasks_q.put_nowait(None)
    log.info("Waiting for listener thread.")
    t.join()
    log.info("Exiting")
