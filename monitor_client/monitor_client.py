"""
Opens a gui (tkinter) on fullscreen to control the monitor placed in the arena,
Random colors from the colors list can be presented, specific colors or images/videos
given their path.

Author: Or Pardilov, 2021

Starts a listening thread for MQTT messages which adds messages to a queue, the main 
thread executes them and maintains the gui.
"""

from tkinter import Tk, Label
from PIL import ImageTk, Image
import cv2
import paho.mqtt.client as mqtt
import queue
import os
import random
import config

ENCODING = "utf-8"

# loading colors list
COLORS = []
with open("color_lst.txt", "r") as cfile:
    for line in cfile:
        COLORS.append(line.strip())


def on_connect(client, userdata, flags, rc):
    print("[INFO] Connected to mqtt broker with result code " + str(rc))


def on_disconnect(client, userdata, rc):
    print("[INFO] Disconnected from mqtt broker with result code " + str(rc))


def on_message(client, userdata, message):
    print("[INFO] message received ", str(message.payload.decode(ENCODING)))
    print("[INFO] message topic=", message.topic)
    payload = str(message.payload.decode(ENCODING))
    # messages are added to a queue to avoid messages drop
    fs.tasks_q.put_nowait((message.topic, payload))


class FsWindow:
    """FsWindow class wraps the GUI data and variables"""

    def __init__(self):
        self.tki = Tk()
        # starts GUI on fullscreen
        self.tki.attributes("-fullscreen", True)
        self.panel = Label(self.tki)
        self.panel.pack()

        self.tki.bind("<Escape>", self.exit_fs)
        self.tki.bind("<F>", self.enter_fs)

        self.vid_cap = None
        self.vid_loop = True
        self.vid_stop = False

        self.size = (self.tki.winfo_screenwidth(), self.tki.winfo_screenheight())
        self.tasks_q = queue.Queue()

    def update_size(self):
        self.size = (self.tki.winfo_screenwidth(), self.tki.winfo_screenheight())

    def enter_fs(self, event=None):
        self.tki.attributes("-fullscreen", True)

    def exit_fs(self, event=None):
        self.tki.attributes("-fullscreen", False)

    def load_img(self, im_path):
        # loads image from a given path to screen
        pil_image = Image.open(im_path)
        # resizing
        width, height = pil_image.size
        w, h = self.tki.winfo_screenwidth(), self.tki.winfo_screenheight()
        ratio = min(w / width, h / height)
        width = int(width * ratio)
        height = int(height * ratio)
        pil_image = pil_image.resize((width, height), Image.ANTIALIAS)
        # presenting
        imgtk = ImageTk.PhotoImage(pil_image)
        self.panel.imgtk = imgtk
        self.panel.configure(image=self.panel.imgtk)

    def load_video(self, vid_path):
        # starts the presentation of a video
        self.update_size()
        self.vid_cap = cv2.VideoCapture(vid_path)
        self.player_loop()

    def player_loop(self):
        ready, frame = self.vid_cap.read()

        if ready and not self.vid_stop:
            cv2img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            # cv2img = cv2.resize(cv2img, self.size, interpolation=cv2.INTER_NEAREST)
            cv2img = Image.fromarray(cv2img)
            self.panel.imgtk = ImageTk.PhotoImage(cv2img)
            self.panel.configure(image=self.panel.imgtk)

            self.tki.after(1, self.player_loop)
        else:
            if self.vid_loop and not self.vid_stop:
                self.vid_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # replay the video
                print("rerun")
                self.tki.after(1, self.player_loop)
            else:
                self.vid_cap.release()
                return

    def update_g(self):
        # excuets messages from queue
        if not self.tasks_q.empty():
            msg = self.tasks_q.get()
            topic = msg[0]
            payload = msg[1]
            if topic == "monitor/image":
                if os.path.exists(payload):
                    self.load_img(payload)
                else:
                    print("[ERROR] The image in " + payload + " was not found")
            elif topic == "monitor/play_video":
                if os.path.exists(payload):
                    self.load_video(payload)
                else:
                    print("[ERROR] The video in " + payload + " was not found")
            elif topic == "monitor/stop_video":
                self.vid_stop = True
                self.load_color("black")
            elif topic == "monitor/color":
                self.load_color(payload)
            else:
                print("[ERROR] nothing to do with that topic: " + topic)

        self.tki.after(200, self.update_g)

    def load_color(self, color):
        # loads a color to the screen
        if color == "random":
            color = random.choice(COLORS)
        self.panel.configure(image="")
        self.panel.configure(bg=color, width=fs.size[0], height=fs.size[0])


if __name__ == "__main__":
    fs = FsWindow()
    fs.panel.configure(bg="black", width=fs.size[0], height=fs.size[0])

    msq_client = mqtt.Client()
    msq_client.on_connect = on_connect
    msq_client.on_disconnect = on_disconnect
    msq_client.connect(config.mqtt["host"], config.mqtt["port"])
    msq_client.on_message = on_message
    msq_client.subscribe("monitor/#")
    msq_client.loop_start()

    fs.update_g()
    fs.tki.mainloop()
