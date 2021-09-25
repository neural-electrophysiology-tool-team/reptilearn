import paho.mqtt.client as mqtt
import queue
from serial.tools import list_ports
from serial import Serial
import threading
import json


class SerialMQTTBridge:
    def __init__(self, serial_config, mqtt_config, logger):
        self.log = logger

        # init serial ports
        self.serial_config = serial_config
        self.serials = []
        self.serial_write_locks = {}

        port_list = list_ports.comports()
        for pid in [p["id"] for p in serial_config["ports"]]:
            candidates = [port for port in port_list if pid in port.hwid]
            if len(candidates) == 1:
                port = candidates[0]
                self.log.info(f"(SERIAL) Connecting to port {port.name} ({port.hwid})")
                ser = Serial(port.device, serial_config["baud_rate"])
                self.serials.append(ser)
                self.serial_write_locks[ser.name] = threading.Lock()

        # init mqtt
        self.mqtt_config = mqtt_config
        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_mqtt_connect
        self.mqtt.on_disconnect = self.on_mqtt_disconnect
        self.mqtt.connect(mqtt_config["host"], mqtt_config["port"])
        self.mqtt.on_message = self.on_mqtt_message
        self.mqtt.subscribe(mqtt_config["subscription"])
        self.mqtt_q = queue.Queue()

        # start threads

        self.mqtt_listen_thread = threading.Thread(target=self.mqtt_listen)
        self.serial_listen_threads = {}

        for s, port_conf in zip(self.serials, self.serial_config["ports"]):
            self.serial_listen_threads[s.name] = threading.Thread(
                target=self.serial_listen, args=[s, port_conf]
            )

        self.shutdown_event = threading.Event()
        self.mqtt_listen_thread.start()
        for t in self.serial_listen_threads.values():
            t.start()

        self.mqtt.loop_start()

    def shutdown(self):
        # stop mqtt_listen_thread
        self.mqtt.loop_stop()
        self.mqtt_q.put_nowait(None)

        # stop serial_listen threads
        self.shutdown_event.set()
        for s in self.serials:
            s.close()

    def serial_listen(self, s: Serial, port_config):
        s.timeout = 1  # TODO

        self.log.info(
            f"(SERIAL) Starting listening thread for port {port_config['name']} ({s.name})"
        )

        while True:
            try:
                if self.shutdown_event.is_set():
                    break
                
                line = s.readline()
                if len(line) == 0:
                    continue

                self.log.debug(
                    f"(SERIAL) Received {port_config['name']}: {line.decode('utf-8')}".strip()
                )

                topic, payload = line.split(b"#")
                topic = topic.decode("utf-8").strip()
                payload = payload.decode("utf-8").strip()

                if topic == "status" and payload == "Waiting for configuration...":
                    try:
                        with open(port_config["config_path"], "r") as f:
                            conf = f.read()
                            with self.serial_write_locks[s.name]:
                                s.write(conf.encode('utf-8'))
                        self.log.info(f"(SERIAL) Done sending configuration to port {port_config['name']}.")
                        
                    except Exception:
                        self.log.exception(
                            "(SERIAL) Exception while sending device configuration file."
                        )
                    finally:
                        continue

                if len(topic) > 0:
                    topic = f"{self.mqtt_config['publish_topic']}/{topic}"

                self.log.debug(f"(MQTT  ) Publishing {topic}: {payload}")
                self.mqtt.publish(topic, payload)

            except KeyboardInterrupt:
                pass

        self.log.info(f"(SERIAL) Terminating listening thread for port {s.name}")

    def mqtt_listen(self):
        self.log.info("(MQTT  ) Starting listening thread")

        while True:
            try:
                msg = self.mqtt_q.get(block=True)

                if msg is None:
                    break

                self.log.debug(
                    f"(SERIAL) Sending message: {msg.payload.decode('utf-8')}"
                )

                for s in self.serials:
                    with self.serial_write_locks[s.name]:
                        s.write(msg.payload + b"\n")

            except KeyboardInterrupt:
                pass

        self.log.info("(MQTT  ) Terminating listening thread")

    def on_mqtt_connect(self, client, userdata, flags, rc):
        self.log.info(f"(MQTT  ) Connected to broker with result code {rc}")

    def on_mqtt_disconnect(self, client, userdata, rc):
        self.log.info(f"(MQTT  ) Disconnected from broker with result code {rc}")

    def on_mqtt_message(self, client, userdata, message):
        self.log.debug(
            f"(MQTT  ) Received {message.topic}: {message.payload.decode('utf-8')}"
        )
        self.mqtt_q.put_nowait(message)
