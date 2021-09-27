import paho.mqtt.client as mqtt
import queue
from serial.tools import list_ports
from serial import Serial
import threading
import json


def serial_port_by_id(id):
    port_list = list_ports.comports()
    candidates = [port for port in port_list if id in port.hwid]
    if len(candidates) == 1:
        return candidates[0]

    raise ValueError(f"Found zero or multiple candidates for port id '{id}'")


class SerialMQTTBridge:
    def __init__(self, config, logger):
        self.log = logger

        # init serial ports
        self.serial_config = config.serial
        self.mqtt_config = config.mqtt
        
        self.serials = {}
        self.serial_write_locks = {}

        for port_name, port_conf in self.serial_config["ports"].items():
            if "id" not in port_conf:
                raise ValueError(f"Invalid serial port config in port {port_name}")

            try:
                port = serial_port_by_id(port_conf["id"])
            except Exception:
                self.log.exception("Exception while getting port info:")

            self.log.info(
                f"(SERIAL) Connecting to port {port_name} ({port.name}, hwid:{port.hwid})"
            )
            ser = Serial(port.device, self.serial_config["baud_rate"])
            self.serials[port_name] = ser
            self.serial_write_locks[ser.name] = threading.Lock()

        if len(self.serials) == 0:
            raise ValueError("No serial ports found")

        # init mqtt
        self.mqtt_config = config.mqtt
        self.mqtt = mqtt.Client()
        self.mqtt.on_connect = self.on_mqtt_connect
        self.mqtt.on_disconnect = self.on_mqtt_disconnect
        self.mqtt.connect(self.mqtt_config["host"], self.mqtt_config["port"])
        self.mqtt.on_message = self.on_mqtt_message
        self.mqtt.subscribe(self.mqtt_config["subscription"])
        self.mqtt_q = queue.Queue()

        # start threads

        self.mqtt_listen_thread = threading.Thread(target=self.mqtt_listen)
        self.serial_listen_threads = {}

        try:
            with open(config.arena_config_path, "r") as f:
                self.arena_conf = json.load(f)
        except json.JSONDecodeError as e:
            self.log.exception("While decoding {config_path}:")
            raise e

        if type(self.arena_conf) is not dict:
            raise ValueError("The arena config json root is expected to be an object.")

        self.interface_dispatcher = {}

        for port_name, port_conf in self.arena_conf.items():
            for interface_name in [ifs["name"] for ifs in port_conf]:
                if interface_name in self.interface_dispatcher:
                    raise ValueError(
                        "Found duplicate interface names in arena config file."
                    )

                self.interface_dispatcher[interface_name] = port_name

        for s, (port_name, port_conf), device_conf in zip(
            self.serials.values(),
            self.serial_config["ports"].items(),
            self.arena_conf.values(),
        ):
            self.serial_listen_threads[s.name] = threading.Thread(
                target=self.serial_listen, args=[s, port_name, port_conf, device_conf]
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
        for s in self.serials.values():
            s.close()

    def serial_listen(self, s: Serial, port_name, port_config, device_conf):
        self.log.info(
            f"(SERIAL) Starting listening thread for port {port_name} ({s.name})"
        )

        while True:
            try:
                if self.shutdown_event.is_set():
                    break

                if s.fd is None:
                    break

                line = s.readline()
                if len(line) == 0:
                    continue

                self.log.debug(
                    f"(SERIAL) [{port_name}]: {line.decode('utf-8')}".strip()
                )

                topic, payload = line.split(b"#")
                topic = topic.decode("utf-8").strip()
                payload = payload.decode("utf-8").strip()

                if topic == "status" and payload == "Waiting for configuration...":
                    try:
                        with self.serial_write_locks[s.name]:
                            s.write(
                                json.dumps({port_name: device_conf}).encode("utf-8")
                            )
                        self.log.info(
                            f"(SERIAL) Done sending configuration to port {port_name}."
                        )

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

                try:
                    command = json.loads(msg.payload)
                except json.JSONDecodeError:
                    self.log.exception("Error while decoding mqtt command:")
                    continue

                if type(command) is not list:
                    self.log.error(
                        "Expecting incoming mqtt command to be a json array."
                    )
                    continue

                cmd_name = command[0]
                cmd_interface = command[1]
                if cmd_interface == "all":
                    for s, conf in zip(
                        self.serials.values(), self.serial_config["ports"].values()
                    ):
                        if not self.is_command_allowed(cmd_name, conf):
                            continue

                        with self.serial_write_locks[s.name]:
                            s.write(msg.payload + b"\n")

                else:
                    port_name = self.interface_dispatcher[cmd_interface]

                    if port_name not in self.serials.keys():
                        self.log.error("Unknown interface: {cmd_interface}")
                        continue

                    port_conf = self.serial_config["ports"][port_name]
                    if not self.is_command_allowed(cmd_name, port_conf):
                        self.log.debug(
                            f"(SERIAL) Ignoring. Port {port_name} does not allow {cmd_name} commands"
                        )
                        continue

                    self.log.debug(f"(SERIAL) Dispatching command to port {port_name}")

                    ser = self.serials[port_name]
                    with self.serial_write_locks[ser.name]:
                        ser.write(msg.payload + b"\n")

            except KeyboardInterrupt:
                pass

        self.log.info("(MQTT  ) Terminating listening thread")

    def is_command_allowed(self, cmd_name, port_conf):
        if (
            cmd_name == "get"
            and "allow_get" in port_conf
            and port_conf["allow_get"] is False
        ):
            return False
        return True

    def on_mqtt_connect(self, client, userdata, flags, rc):
        self.log.info(f"(MQTT  ) Connected to broker with result code {rc}")

    def on_mqtt_disconnect(self, client, userdata, rc):
        self.log.info(f"(MQTT  ) Disconnected from broker with result code {rc}")

    def on_mqtt_message(self, client, userdata, message):
        self.log.debug(f"(MQTT  ) {message.topic}: {message.payload.decode('utf-8')}")
        self.mqtt_q.put_nowait(message)
