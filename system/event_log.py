import multiprocessing as mp
import functools
import threading
import mqtt
import time
import json
import managed_state
from data_log import DataLogger
from json_convert import json_convert


class EventDataLogger(DataLogger):
    def __init__(self, config, table_name="events", *args, **kwargs):
        super().__init__(
            columns=(
                ("time", "timestamptz not null"),
                ("event", "varchar(128)"),
                ("value", "json"),
            ),
            table_name=table_name,
            *args,
            **kwargs,
        )

        self._event_q = mp.Queue()
        self._add_event_q = mp.Queue()
        self._remove_event_q = mp.Queue()
        self._connect_mqtt_event = mp.Event()
        self._connect_state_event = mp.Event()
        self._mqtt_config = config.mqtt
        self._state_store_address = config.state_store_address
        self._mqttc = None

    def run(self):
        self._state = managed_state.Cursor((), address=self._state_store_address)
        self._state_dispatcher = managed_state.StateDispatcher(self._state)

        self._mqttc = mqtt.MQTTClient(
            self._mqtt_config["host"], self._mqtt_config["port"]
        )
        self._mqttc.connect(on_success=lambda: self._connect_mqtt_event.set())
        threading.Thread(target=self._state_dispatcher.listen).start()
        self._mqttc.loop_start()

        super().run()

        self._mqttc.loop_stop()
        self._mqttc.disconnect()
        self._state_dispatcher.stop()

    def start(self, wait=False):
        super().start()

        if wait is False:
            return True

        timeout = wait if type(wait) is int else None
        # TODO: should we wait for the state dispatcher to init? is it necessary?

        if self._connect_mqtt_event.wait(timeout):
            self._connect_mqtt_event.clear()
            return True
        else:
            # timeout has passed
            return False

    def _log_mqtt(self, topic, payload):
        self._event_q.put((time.time(), topic, payload))

    def _log_state(self, path, old, new):
        self._event_q.put((time.time(), path, new))

    def _register_event(self, event):
        src, key = event
        if src == "mqtt":
            self._mqttc.subscribe_callback(key, mqtt.mqtt_json_callback(self._log_mqtt))
        elif src == "state":
            self._state_dispatcher.add_callback(
                key, functools.partial(self._log_state, key)
            )
        else:
            raise ValueError(f"Unknown src: {src}")

    def _unregister_event(self, event):
        src, key = event
        if src == "mqtt":
            self._mqttc.unsubscribe(key)
        elif src == "state":
            self._state_dispatcher.remove_callback(key)

    def add_mqtt_event(self, topic):
        self.add_event("mqtt", topic)

    def add_state_event(self, path):
        self.add_event("state", path)

    def add_event(self, src, key):
        self._add_event_q.put((src, key))

    def log(self, event, value):
        self._event_q.put((time.time(), event, value))

    def stop(self):
        self._event_q.put(None)

    def remove_mqtt_event(self, topic):
        self.remove_event("mqtt", topic)

    def remove_state_event(self, path):
        self.remove_event("state", path)

    def remove_event(self, src, key):
        self._remove_event_q.put((src, key))

    def _get_data(self):
        while True:
            if not self._add_event_q.empty():
                self._register_event(self._add_event_q.get())

            if not self._remove_event_q.empty():
                self._unregister_event(self._remove_event_q.get())

            try:
                event = self._event_q.get(timeout=1)
            except KeyboardInterrupt:
                pass
            except mp.queues.Empty:
                pass
            else:
                if event is not None:
                    self.logger.debug(f"Logging event: {event}")
                    return (
                        event[0],
                        event[1],
                        json.dumps(event[2], default=json_convert),
                    )
                else:
                    return None
