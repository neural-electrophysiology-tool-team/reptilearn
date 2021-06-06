"""
Provide connectivity between MQTT messages and sensor/ttl arduinos, handles periodic polling of the temperature
and humidity sensors reading
Author: Or Pardilov, 2021

Starts a listening thrread for MQTT messages while adds messages to the queue, a working thread for handling the queued
messages and a thread to handle the periodic sensors polling.
"""


import paho.mqtt.client as mqtt
import time
import threading
import serial
import json
import serial.tools.list_ports as ports
import logging
import queue
import sys
import config

# logging configs
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="[%(levelname)s] - %(asctime)s: %(message)s",
)
g_log = logging.getLogger("Arena")

# Default values, will get those from config
endFlag = 0
ENCODING = "utf-8"


def on_connect(client, userdata, flags, rc):
    g_log.info("Connected to mqtt broker with result code " + str(rc))


def on_disconnect(client, userdata, rc):
    g_log.info("Disconnected from mqtt broker with result code " + str(rc))


def json_or_not(payload):
    try:
        payload_in_json = json.loads(payload)
    except:
        payload_in_json = False
    if payload_in_json:
        return True
    else:
        if "on" in payload.lower():
            return True
        else:
            return False


def communicator_routine():
    """communicator routine is the main routine of the mosquitto client thread,
    Whenever a message is available for popping from the queue, it will be executed from this
    thread"""
    while True:
        msg_cont = g_client.msg_q.get(block=True)
        topic = msg_cont[0]
        payload = msg_cont[1]

        if topic == "arena/dispense_reward":
            g_log.info("Sending reward")
            g_client.digital_writes("Reward 0 0\n")
        elif topic == "arena/signal_led":
            g_client.digital_writes(
                "Led 0 " + ("1" if json_or_not(payload) else "0") + "\n"
            )  # TODO: only one led for now
        elif topic == "arena/day_lights":
            g_client.digital_writes(
                "Lights 0 " + ("1" if json_or_not(payload) else "0") + "\n"
            )  # TODO: only one light for now
        elif "arena/line" in topic:
            line_num = topic.partition("line/")[2].strip()
            if line_num.isnumeric():
                g_client.digital_writes(
                    "Dig "
                    + line_num
                    + " "
                    + ("1" if json_or_not(payload) else "0")
                    + "\n"
                )
            else:
                g_log.error("Digital line value is not a number : " + line_num)
        elif topic == "arena/ttl_trigger/start":
            g_client.start_trigger(payload)
        elif topic == "arena/ttl_trigger/stop":
            g_client.stop_trigger()
        elif topic == "arena/sensors/poll":
            g_client.sensor_poll()
        else:
            g_log.error("[ERROR] could not figure out message " + str(payload))


def on_message(client, userdata, message):
    g_log.info("[INFO] message received ", str(message.payload.decode(ENCODING)))
    g_log.info("[INFO] message topic=", message.topic)
    payload = str(message.payload.decode(ENCODING))

    # Messages are added to the message queue to prevent message losses
    if message.topic == "arena/sensors/set_interval":
        if payload.isnumeric():
            g_client.period = int(payload)
            g_log.info("[INFO] Updated sensor interval to " + payload + " min")
    else:
        g_client.msg_q.put_nowait((message.topic, payload))


class TempClient:
    def __init__(self, sens_arduino, trigger_arduino):
        self.period = config.poll_interval
        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.connect(config.mqtt["host"], config.mqtt["port"])
        self.client.on_message = on_message
        self.client.subscribe("arena/dispense_reward")
        self.client.subscribe("arena/signal_led")
        self.client.subscribe("arena/day_lights")
        self.client.subscribe("arena/ttl_trigger/#")
        self.client.subscribe("arena/line/#")
        self.client.subscribe("arena/sensors/poll")
        self.client.subscribe("arena/sensors/set_interval")

        # Locks for making the serial connection with the arduino's thread safe
        self.sens_arduino = sens_arduino
        self.sens_lock = threading.Lock()

        self.trigger_arduino = trigger_arduino
        self.trigger_lock = threading.Lock()

        self.msg_q = queue.Queue()

    def sensor_poll(self):
        # Handling Poll request
        with self.sens_lock:
            self.sens_arduino.write(str.encode("Temppoll 0 0\n"))
            g_log.info("waiting for feedback")
            sensors_info = self.sens_arduino.readline()
            g_log.info("Received Sensors info: " + sensors_info.decode(ENCODING))
        sensors_info = sensors_info.decode(ENCODING).strip().split(";")
        trans_dict = {}
        # Publishing the result as json dict
        for info in sensors_info:
            serial_num = info.partition("Sensor_")[2].split(" ")[0]
            reading = info.partition(":")[2].replace(" ", "")
            if not reading:
                continue
            key = "temp" if reading.endswith("C") else "humidity"
            reading = float(reading.replace("H", "").replace("C", ""))
            if key in trans_dict.keys():
                trans_dict[key].append(reading)
            else:
                trans_dict[key] = [reading] if key == "temp" else reading
        json_dict = json.dumps(trans_dict)
        self.client.publish("arena/sensors", json_dict)

    def start_trigger(self, json_dump):
        try:
            local_d = {}
            trigger_info = json.loads(json_dump)
            if isinstance(trigger_info, dict):  # if indeed a dict received
                local_d = trigger_info
            send_str = (
                "START "
                + (str(local_d["pulse_len"]) if "pulse_len" in local_d else "17")
                + " "
                + (str(local_d["pulse_width"]) if "pulse_width" in local_d else "0.7")
                + " "
                + (str(local_d["ttl_count"]) if "ttl_count" in local_d else "0")
                + " "
                + (
                    str(local_d["serial_trigger"])
                    if "serial_trigger" in local_d
                    else "1"
                )
                + "\n"
            )
            with self.sens_lock:
                if self.trigger_arduino:
                    self.trigger_arduino.write(str.encode(send_str))
                    g_log.info("START TRIGGER: sent " + send_str)
        except Exception as e:
            g_log.error("while sending start trigger : " + str(e))
            return

    def stop_trigger(self):
        with self.sens_lock:
            if self.trigger_arduino:
                self.trigger_arduino.write(str.encode("STOP\n"))

    def digital_writes(
        self, payload
    ):  # Sending digital high signals (or any serial communication)
        with self.sens_lock:
            self.sens_arduino.write(str.encode(payload))

    def disconnect_cl(self):
        self.client.loop_stop()
        self.client.disconnect(reasoncode=0)


def sleeper_routine():  # checks on the temperature every second
    while not endFlag:
        g_client.sensor_poll()
        time.sleep(g_client.period)


if __name__ == "__main__":
    ports_list = [tuple(p) for p in list(ports.comports())]
    if not ports_list:
        g_log.error("No ports detected, quitting")
        exit(-1)

    g_log.info("ports list:\n" + "\n".join([",".join(i) for i in ports_list]))
    TriggerArduino = False

    # searching for the known arduino's serial numbers on the ports list
    if [
        tuples[2]
        for tuples in ports_list
        if config.arduino["arena_serial"] in tuples[2]
    ]:
        g_log.info(
            "Connecting to "
            + [
                tuples[1]
                for tuples in ports_list
                if config.arduino["arena_serial"] in tuples[2]
            ][0]
            + " as sensors arduino"
        )
        arena_port = [
            tuples[0]
            for tuples in ports_list
            if config.arduino["arena_serial"] in tuples[2]
        ][0]
        g_log.info("Arena port: " + arena_port)
        SensArduino = serial.Serial(arena_port, 115200)  # connect to sensors arduino
        time.sleep(0.5)
        while SensArduino.in_waiting:
            g_log.info("[SENS] " + SensArduino.readline().decode(ENCODING))
    if [
        tuples[2] for tuples in ports_list if config.arduino["ttl_serial"] in tuples[2]
    ]:
        g_log.info(
            "Connecting to "
            + [
                tuples[1]
                for tuples in ports_list
                if config.arduino["ttl_serial"] in tuples[2]
            ][0]
            + " as trigger arduino"
        )
        ttl_port = [
            tuples[0]
            for tuples in ports_list
            if config.arduino["ttl_serial"] in tuples[2]
        ][0]
        TriggerArduino = serial.Serial(ttl_port, 115200)  # connect to ttl arduino

    # creating TempClient instance
    g_client = TempClient(sens_arduino=SensArduino, trigger_arduino=TriggerArduino)

    # starting the listening thread
    g_client.client.loop_start()  # starts a new thread to handle network stuff
    th_msg = threading.Thread(target=communicator_routine, args=[])
    th_slp = threading.Thread(target=sleeper_routine, args=[])

    # start a thread to check temp
    time.sleep(1)  # wait for connection
    th_msg.start()
    th_slp.start()

    # wait for user input
    while True:
        user_input = input("Type message to publish to 'test', or exit to terminate\n")
        if user_input.lower() == "exit":
            endFlag = True
            g_client.disconnect_cl()
            break
        else:
            g_client.client.publish("Test", user_input)
