import config
import paho.mqtt.client as paho
import logging
import json


class Client:
    def __init__(self, host=config.mqtt["host"], port=config.mqtt["port"], logger=logging.getLogger("MQTTClient")):
        self.client = paho.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.host = host
        self.port = port
        self.log = logger
        
        self.is_connected = False
        self.dispatch_table = []

    def connect(self, **kwargs):
        self.client.connect(host=self.host, port=self.port, **kwargs)

    def disconnect(self):
        if self.connected:
            self.client.disconnect()
            self.is_connected = False
            # might be good to wait for publish before disconnecting

    def register_listener(self, topic, on_message):
        self.dispatch_table.append((topic, on_message))

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.log.info(f"MQTT connected successfully to {self.host}:{self.port}.")
            self.is_connected = True
            client.subscribe([(sub, 0) for sub, handler in self.dispatch_table])
        else:
            self.log.error(f"MQTT connection refused (rc code {rc}).")

    def on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8")
        self.log.info(f"Received MQTT message with topic {msg.topic}")
        for sub, handler in self.dispatch_table:
            if paho.topic_matches_sub(sub, msg.topic):
                handler(msg.topic, payload)

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.client.publish(topic, payload, qos, retain)

    def publish_json(self, topic, payload=None, qos=0, retain=False):
        self.client.publish(topic, json.dumps(payload), qos, retain)
        
    def listen(self):
        self.log.info("Listening for MQTT messages.")
        self.client.loop_forever()
