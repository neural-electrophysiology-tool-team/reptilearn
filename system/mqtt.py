import config
import paho.mqtt.client as paho
import logging
import json
import logging


class MQTTClient(paho.Client):
    def __init__(self):
        super().__init__()
        self.is_connected = False
        self.on_connect_subscriptions = []
        self.on_connect_callback = None
        self.subscribed_topics = []
        self.last_msg_info = None
        self.log = logging.getLogger("MQTTClient")
        
    def disconnect(self):
        if self.is_connected:
            self.log.info("MQTT disconnecting...")
            self.last_msg_info.wait_for_publish()
            super().disconnect()
            self.is_connected = False

    def connect(self, on_success=None):
        if on_success is not None:
            self.on_connect_callback = on_success

        super().connect(**config.mqtt)

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            host, port = config.mqtt["host"], config.mqtt["port"]
            self.log.info(f"MQTT connected successfully to {host}:{port}.")
            self.is_connected = True
            for topic, callback in self.on_connect_subscriptions:
                self.subscribe_callback(topic, callback)

            if self.on_connect_callback is not None:
                self.on_connect_callback()
                self.on_connect_callback = None
        else:
            self.log.error(f"MQTT connection refused (rc code {rc}).")

    def subscribe_callback(self, topic, callback):
        if not self.is_connected:
            self.on_connect_subscriptions.append((topic, callback))

        self.subscribed_topics.append(topic)
        self.subscribe(topic)
        self.message_callback_add(topic, callback)

    def unsubscribe_all(self):
        for topic in self.subscribed_topics:
            self.message_callback_remove(topic)
            self.unsubscribe(topic)

        self.subscribed_topics.clear()

    def publish_json(self, topic, payload=None, **kwargs):
        self.publish(topic, json.dumps(payload), **kwargs)

    def publish(self, *args, **kwargs):
        self.last_msg_info = super().publish(*args, **kwargs)


def mqtt_json_callback(callback):
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


def init(logger):
    global client
    client = MQTTClient()
    client.log = logger
    client.loop_start()
    client.connect()


def shutdown():
    client.disconnect()
    client.loop_stop()
