"""
Monitor hardware controller
Author: Or Pardilov, 2021

Provides convenience functions for communicating with the monitor program over MQTT
"""
import mqtt


def change_color(color="random"):
    #if a color is not given, let the application choose a random color
    mqtt.client.publish(topic="monitor/color", payload=color)


def show_image(path):
    mqtt.client.publish(topic="monitor/image", payload=str(path))


def play_video(path):
    mqtt.client.publish(topic="monitor/play_video", payload=str(path))


def stop_video():
    mqtt.client.publish(topic="monitor/stop_video", payload="")
