"""
A data logger for logging experiment events.

Author: Tal Eisenberg, 2021
"""
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
    """
    The EventDataLogger is a DataLogger (running on a child process) that logs experiment events.
    The logger is started whenever a session is loaded, and it is stopped when the session is closed (see experiment.py).
    It can be set up to log MQTT messages and state store updates, as well as custom experiment events.
    The logger can be configured in the config module under the event_log dictionary.

    Events can be stored in a .csv file or a TimescaleDB hypertable (or both), and uses the following columns:
    - time: Event timestamp in seconds since epoch
    - event: The event name (up to 128 characters for the db table)
    - value: A JSON blob containing more information about the event

    config.event_log options:
    - default_events: A list of MQTT or state update events that will be logged in every experiment.
                      Each element should be a tuple.
                      - To add an MQTT default event use: ('mqtt', mqtt_topic), for example
                        ("mqtt", "arena_command") will log all arena commands.
                      - To log every update to a specific state path use: ("state", state_path), for example
                        ("state", ("session", "cur_trial"))
    - log_to_db: Whether to log events to the database.
    - log_to_csv: Whether to log events to csv files.
    - table_name: The name of the database table where events will be stored.

    MQTT and state events can be added or removed after the logger is started. See methods below
    To log custom events the log method can be used.
    """

    def __init__(self, config, db_table_name="events", *args, **kwargs):
        super().__init__(
            columns=(
                ("time", "timestamptz not null"),
                ("event", "varchar(128)"),
                ("value", "json"),
            ),
            db_table_name=db_table_name,
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
        self._state_store_authkey = config.state_store_authkey
        self._mqttc = None

    def run(self):
        self._state = managed_state.Cursor(
            (), authkey=self._state_store_authkey, address=self._state_store_address
        )
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

    def add_event(self, src, key):
        """
        Start logging when an MQTT or state event occurs.

        Args:
        - src: Either "mqtt" or "state" for listening to MQTT messages or state store updates, respectively.
        - key: In the case of an "mqtt" src. the key is an MQTT topic (a string. may include wildcards). In the case of a "state"
               src, the key is a state store path (any state path type, see dicttools.py).
        """
        self._add_event_q.put((src, key))

    def log(self, event, value):
        """
        Add a log record (row) with current time, and the supplied event and value.
        """
        self._event_q.put((time.time(), event, value))

    def stop(self):
        """
        Shutdown the logger process.
        """
        self._event_q.put(None)

    def remove_mqtt_event(self, topic: str):
        """
        Unsubscribe from MQTT `topic`.
        Stop logging when something publishes to `topic`.
        """
        self._remove_event("mqtt", topic)

    def remove_state_event(self, path):
        """
        Stop logging when the supplied state store path updates.
        """
        self._remove_event("state", path)

    def _remove_event(self, src, key):
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
