import mqtt
import json
from rl_logging import get_main_logger
import time
import threading
import asyncio


class Canvas:
    def __init__(self, canvas_id):
        self.canvas_id = canvas_id

        self.subscription_topic = f"canvas/{canvas_id}/out"
        self.outgoing_topic = f"canvas/{canvas_id}/in"

        mqtt.client.subscribe_callback(
            self.subscription_topic + "/#",
            mqtt.mqtt_json_callback(self.handle_mqtt_response),
        )

        self.log = get_main_logger()

        self.result_handlers = {}
        self.result_handlers_lock = threading.Lock()
        self.error_handlers = {}
        self.error_handlers_lock = threading.Lock()
        self.node_handlers = {}
        self.node_handlers_lock = threading.Lock()
        self.image_handlers = {}
        self.image_handlers_lock = threading.Lock()
        self.video_handlers = {}
        self.video_handlers_lock = threading.Lock()
        self.tween_handlers = {}
        self.tween_handlers_lock = threading.Lock()
        self.on_connect = None
        self.on_unload = None

        self.log.info(f"Initialized canvas with id {canvas_id}")

    def release(self):
        mqtt.client.unsubscribe_callback(self.subscription_topic + "/#")

    def handle_mqtt_response(self, topic, payload):
        tlen = len(self.subscription_topic) + 1
        topic = topic[tlen:]
        # self.log.debug(f"MQTT message received. canvas={self.canvas_id} topic={topic} payload={payload}")

        if topic == "result":
            # log.debug(f"Received result: {payload}")
            ts = payload["request"].get("request_timestamp", None)
            if ts is None:
                return

            if ts in self.result_handlers:
                self.result_handlers[ts](payload)
                with self.result_handlers_lock:
                    if ts in self.result_handlers:
                        del self.result_handlers[ts]
            if ts in self.error_handlers:
                with self.error_handlers_lock:
                    del self.error_handlers[ts]

        elif topic == "error":
            self.log.error(f"Received error: {payload}")
            ts = payload["request"].get("request_timestamp", None)
            if ts is None:
                return

            if ts in self.error_handlers:
                self.error_handlers[ts](payload)
                with self.error_handlers_lock:
                    del self.error_handlers[ts]
            if ts in self.result_handlers:
                with self.result_handlers_lock:
                    del self.result_handlers[ts]

        elif topic == "on":
            self.handle_node_event(payload)

        elif topic == "connected":
            if self.on_connect:
                self.on_connect()
        elif topic == "unloading":
            if self.on_unload:
                self.on_unload()

        elif topic == "image_onload":
            self.handle_image_onload(payload)

        elif topic == "image_onerror":
            self.handle_image_onerror(payload)

        elif topic == "video_loadedmetadata":
            self.handle_video_loadedmetadata(payload)

        elif topic == "video_error":
            self.handle_video_error(payload)

        elif topic == "tween_on_update":
            self.handle_tween_on_update(payload)

        elif topic == "tween_on_finish":
            self.handle_tween_on_finish(payload)

    def handle_request(self, topic, payload):
        # self.log.debug(f"MQTT publishing canvas={self.canvas_id} topic={topic} payload={payload}")
        mqtt.client.publish(f"{self.outgoing_topic}/{topic}", json.dumps(payload))

    async def wait(self, fn, *args, timeout=5, **kwargs):
        loop = asyncio.get_running_loop()
        f = loop.create_future()

        def on_result(resp):
            async def set_result():
                f.set_result(resp)

            asyncio.run_coroutine_threadsafe(set_result(), loop=loop)

        def on_error(resp):
            async def set_exception():
                f.set_exception(Exception(f"Error while waiting: {resp}"))

            self.log.info(f"Error while waiting: {resp}")
            asyncio.run_coroutine_threadsafe(set_exception(), loop=loop)

        fn(*args, **kwargs, on_result=on_result, on_error=on_error)

        return await asyncio.wait_for(f, timeout=timeout, loop=loop)

    def send_command(self, topic, payload, on_result=None, on_error=None):
        ts = time.time()
        payload["request_timestamp"] = ts
        if on_result is not None:
            with self.result_handlers_lock:
                self.result_handlers[ts] = on_result

        if on_error is not None:
            with self.error_handlers_lock:
                self.error_handlers[ts] = on_error

        self.handle_request(topic, payload)

        return ts

    def add(
        self,
        container_id: str,
        node_class: str,
        on_result=None,
        on_error=None,
        **kwargs,
    ):
        self.send_command(
            "add",
            {
                "container_id": container_id,
                "node_class": node_class,
                "node_config": kwargs,
            },
            on_result=on_result,
            on_error=on_error,
        )

    def node(self, node_id: str, method: str, *args, on_result=None, on_error=None):
        self.send_command(
            "node",
            {"node_id": node_id, "method": method, "args": args},
            on_result=on_result,
            on_error=on_error,
        )

    def get_node(self, node_id: str, on_result=None, on_error=None):
        def handle_result(res):
            on_result(res.get("result", None))

        self.node(node_id, "toObject", on_result=handle_result, on_error=on_error)

    def handle_node_event(self, payload):
        self.log.debug(f"Received event payload={payload}")

        if "target" in payload["event"]:
            payload["event"]["target"] = json.loads(payload["event"]["target"])

        target_id = payload["event"]["target"]["attrs"].get("id", None)
        if target_id is None:
            target_id = "stage"

        handler = self.node_handlers.get((target_id, payload["event"]["type"]), None)
        if handler is not None:
            handler(payload)

    def handle_image_onload(self, payload):
        handler = self.image_handlers.get(payload["image_id"], None)["load"]
        if handler is not None:
            handler(payload)
            with self.image_handlers_lock:
                del self.image_handlers[payload["image_id"]]["load"]

    def handle_image_onerror(self, payload):
        handler = self.image_handlers.get(payload["image_id"], None)["error"]
        if handler is not None:
            handler(payload)
            with self.image_handlers_lock:
                del self.image_handlers[payload["image_id"]]["error"]

    def handle_video_loadedmetadata(self, payload):
        handlers = self.video_handlers.get(payload["video_id"], None)
        if handlers is not None:
            handlers["loadedmetadata"](payload)
            with self.video_handlers_lock:
                del self.video_handlers[payload["video_id"]]["loadedmetadata"]

    def handle_tween_on_update(self, payload):
        handlers = self.tween_handlers.get(payload["tween_id"], None)
        if handlers is not None:
            if handlers["on_update"] is not None:
                payload["node"] = json.loads(payload["node"])
                handlers["on_update"](payload)

    def handle_tween_on_finish(self, payload):
        handlers = self.tween_handlers.get(payload["tween_id"], None)
        if handlers is not None:
            if handlers["on_finish"] is not None:
                payload["node"] = json.loads(payload["node"])
                handlers["on_finish"](payload)

    def handle_video_error(self, payload):
        handler = self.video_handlers.get(payload["video_id"], None)["error"]
        if handler is not None:
            handler(payload)
            with self.video_handlers_lock:
                del self.video_handlers[payload["video_id"]]["error"]

    def on(self, node_id, event_name, handler):
        with self.node_handlers_lock:
            self.node_handlers[(node_id, event_name)] = handler

        self.send_command("on", {"node_id": node_id, "event_name": event_name})

    def off(self, node_id, event_name):
        self.send_command("off", {"node_id": node_id, "event_name": event_name})
        with self.node_handlers_lock:
            del self.node_handlers[(node_id, event_name)]

        self.log.debug(f"Removed event handler node_id={node_id} name={event_name}")

    def reset(self, on_result=None, on_error=None):
        def handle_result(payload):
            with self.node_handlers_lock:
                self.node_handlers = {}
            with self.image_handlers_lock:
                self.image_handlers = {}
            with self.result_handlers_lock:
                self.result_handlers = {}
            with self.error_handlers_lock:
                self.error_handlers = {}

            if on_result is not None:
                on_result(payload)

        self.send_command("reset", {}, on_result=handle_result, on_error=on_error)

    def make_tween(
        self,
        tween_id,
        on_result=None,
        on_error=None,
        on_update=None,
        on_finish=None,
        **kwargs,
    ):
        with self.tween_handlers_lock:
            self.tween_handlers[tween_id] = {
                "on_update": on_update,
                "on_finish": on_finish,
            }

        self.send_command(
            "make_tween",
            {
                "tween_id": tween_id,
                "tween_config": kwargs,
            },
            on_result=on_result,
            on_error=on_error,
        )

    def remove_tween(self, tween_id, on_result=None, on_error=None):
        self.send_command(
            "remove_tween",
            {"tween_id": tween_id},
            on_result=on_result,
            on_error=on_error,
        )

    def tween(self, tween_id: str, method: str, *args, on_result=None, on_error=None):
        self.send_command(
            "tween",
            {"tween_id": tween_id, "method": method, "args": args},
            on_result=on_result,
            on_error=on_error,
        )

    def play_tween(self, tween_id: str, on_result=None, on_error=None):
        self.tween(tween_id, "play", on_result=on_result, on_error=on_error)

    def load_image(
        self,
        image_id: str,
        src: str,
        image_onload=None,
        image_onerror=None,
        on_result=None,
        on_error=None,
    ):
        with self.image_handlers_lock:
            self.image_handlers[image_id] = {
                "load": image_onload,
                "error": image_onerror,
            }

        self.send_command(
            "load_image",
            {"image_id": image_id, "src": src},
            on_result=on_result,
            on_error=on_error,
        )

    def remove_image(self, image_id: str, on_result=None, on_error=None):
        self.send_command(
            "remove_image",
            {"image_id": image_id},
            on_result=on_result,
            on_error=on_error,
        )
        with self.image_handlers_lock:
            if image_id in self.image_handlers:
                del self.image_handlers[image_id]

    def load_video(
        self,
        video_id: str,
        src: str,
        video_loadedmetadata=None,
        video_error=None,
        on_result=None,
        on_error=None,
        **kwargs,
    ):
        with self.video_handlers_lock:
            self.video_handlers[video_id] = {
                "loadedmetadata": video_loadedmetadata,
                "error": video_error,
            }

        self.send_command(
            "load_video",
            {"video_id": video_id, "src": src, **kwargs},
            on_result=on_result,
            on_error=on_error,
        )

    def add_video(
        self, container_id: str, video_id: str, on_result=None, on_error=None, **kwargs
    ):
        self.send_command(
            "add_video",
            {"container_id": container_id, "video_id": video_id, "node_config": kwargs},
            on_result=on_result,
            on_error=on_error,
        )

    def remove_video(self, video_id: str, on_result=None, on_error=None):
        self.send_command(
            "remove_video",
            {"video_id": video_id},
            on_result=on_result,
            on_error=on_error,
        )
        with self.video_handlers_lock:
            if video_id in self.video_handlers:
                del self.video_handlers[video_id]

    def play_video(self, video_id: str, on_result=None, on_error=None):
        self.send_command(
            "play_video", {"video_id": video_id}, on_result=on_result, on_error=on_error
        )

    def pause_video(self, video_id: str, on_result=None, on_error=None):
        self.send_command(
            "pause_video",
            {"video_id": video_id},
            on_result=on_result,
            on_error=on_error,
        )

    def video_set_props(self, video_id: str, on_result=None, on_error=None, **props):
        self.send_command(
            "video_set_props",
            {"video_id": video_id, "props": props},
            on_result=on_result,
            on_error=on_error,
        )

    def video_get_props(self, video_id: str, props, on_result=None, on_error=None):
        self.send_command(
            "video_get_props",
            {"video_id": video_id, "props": props},
            on_result=on_result,
            on_error=on_error,
        )
