import mqtt
import schedule


def change_color(color="random"):
    mqtt.client.publish(topic="monitor/color", payload=color)


def show_image(path=""):
    if path:
        mqtt.client.publish(topic="monitor/image", payload=path)


def play_video(path=""):
    if path:
        mqtt.client.publish(topic="monitor/play_video", payload=path)


def stop_video():
    mqtt.client.publish(topic="monitor/stop_video", payload="")
