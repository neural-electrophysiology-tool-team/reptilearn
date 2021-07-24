"""
Monitor hardware controller
Author: Or Pardilov, 2021

Provides convenience functions for communicating with the monitor program over MQTT
"""
import mqtt


def set_color(color="random"):
    """
    Set monitor background color. if a color is not given a random color is chosen.
    """
    mqtt.client.publish(topic="monitor/color", payload=color)


def show_image(path):
    mqtt.client.publish(topic="monitor/image", payload=str(path))


def clear():
    mqtt.client.publish(topic="monitor/clear")


def play_video(path):
    mqtt.client.publish(topic="monitor/play_video", payload=str(path))


def stop_video():
    mqtt.client.publish(topic="monitor/stop_video")


def on_playback_end(callback):
    """
    Subscribe a callback function that will be called once video playback has ended.

    The callback function signature should be callback(timestamps). timestamps is a list of
    [frame_number, playback timestamp] pairs.
    """
    def on_end(_, timestamps):
        callback(timestamps)

    mqtt.client.subscribe_callback("monitor/playback_ended", mqtt.mqtt_json_callback(on_end))


def unsubscribe_playback_end():
    """
    Unsubscribes from video playback end events.
    """
    mqtt.client.unsubscribe_callback("monitor/playback_ended")
