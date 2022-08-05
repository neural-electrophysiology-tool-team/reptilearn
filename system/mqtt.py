"""
This module contains an MQTTClient class that inherits from paho.mqtt.client.Client.
The client is instanstiated in the mqtt.init function, and can be referenced from
mqtt.client.

mqtt.mqtt_json_callback is useful when the incoming message payload is a JSON string.
"""

import paho.mqtt.client as paho
import logging
import json
from configure import get_config
from rl_logging import get_main_logger


class MQTTClient(paho.Client):
    """
    MQTT client based on the paho Client with additional features.
    Logs messages to the MQTTClient logger by default.
    """

    def __init__(self, host, port):
        super().__init__()
        self.host = host
        self.port = port
        self.is_connected = False
        self.subscriptions = {}
        self.on_connect_callback = None

        self.last_msg_info = None
        self.log = logging.getLogger("MQTTClient")

    def disconnect(self):
        """Disconnect after publishing the last message."""
        if self.is_connected:
            self.log.info("MQTT disconnecting...")
            if self.last_msg_info is not None:
                self.last_msg_info.wait_for_publish()
            super().disconnect()
            self.is_connected = False

    def connect(self, on_success=None):
        """
        Connect to the server.
        - on_success: A callback function for successful connection.
        """
        if on_success is not None:
            self.on_connect_callback = on_success

        super().connect(self.host, self.port)

    def on_connect(self, client, userdata, flags, rc):
        if rc == paho.MQTT_ERR_SUCCESS:
            self.log.info(f"MQTT connected successfully to {self.host}:{self.port}.")
            self.is_connected = True
            for topic, callback in self.subscriptions.items():
                self.subscribe_callback(topic, callback)

            if self.on_connect_callback is not None:
                self.on_connect_callback()
                self.on_connect_callback = None
        else:
            self.log.error(f"MQTT connection refused (rc code {rc}).")

    def on_disconnect(self, client, userdata, rc):
        if not rc == paho.MQTT_ERR_SUCCESS:
            self.log.info("Unexpected MQTT client disconnect.")

    def subscribe_callback(self, topic, callback):
        """
        Subscribe a callback function to a topic (str).
        There can only be one callback for each topic.
        """
        self.subscriptions[topic] = callback
        self.subscribe(topic)
        self.message_callback_add(topic, self._exception_handler_wrapper(callback))

    def unsubscribe_all(self):
        """Unsubscribe all previous subscriptions and remove callbacks."""
        for topic in self.subscriptions.keys():
            self.message_callback_remove(topic)
            self.unsubscribe(topic)

        self.subscriptions.clear()

    def unsubscribe_callback(self, topic):
        if topic in self.subscriptions:
            self.message_callback_remove(topic)
            self.unsubscribe(topic)
            return self.subscriptions.pop(topic)
        else:
            return None

    def publish_json(self, topic, payload=None, **kwargs):
        """Convert the payload to JSON and publish to topic."""
        self.publish(topic, json.dumps(payload), **kwargs)

    def publish(self, *args, **kwargs):
        """Publish a message. See paho.Client.publish for details."""
        self.last_msg_info = super().publish(*args, **kwargs)

    def _exception_handler_wrapper(self, callback):
        def cb(*args, **kwargs):
            try:
                callback(*args, **kwargs)
            except Exception:
                self.log.exception("Exception raised while running MQTT callback:")

        return cb


def mqtt_json_callback(callback):
    """
    Wrap the callback function with json decoding.
    Returns a function that can be used with MQTTClient.subscribe_callback.

    The callback signature should be (topic, payload) where:
    - topic: str, the message topic,
    - payload: dict, the decoded json message.
    """

    def cb(client, userdata, message):
        payload = message.payload.decode("utf-8")
        if len(payload) == 0:
            payload = None
        if payload is not None:
            try:
                payload = json.loads(payload)
            except json.decoder.JSONDecodeError:
                pass

        callback(message.topic, payload)

    return cb


# Main process threaded client
client = None


def init():
    """
    Create an MQTTClient and run it in a new thread.
    The client is accessible through mqtt.client.

    - logger: Client logger
    """
    global client
    client = MQTTClient(get_config().mqtt["host"], get_config().mqtt["port"])
    client.log = get_main_logger()
    client.loop_start()
    client.log.info("Connecting to MQTT server...")
    client.connect()


def shutdown():
    client.disconnect()
    client.loop_stop()
