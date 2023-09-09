"""
Canvas MQTT interface
Author: Tal Eisenberg (2023)
"""

import mqtt
import json
import time
import threading
import asyncio
from rl_logging import get_main_logger


class Canvas:
    """
    Class representing a connection to a Canvas browser app.
    """

    def __init__(
        self,
        canvas_id,
        on_connect=None,
        on_disconnect=None,
        event_loop=None,
        logger=None,
    ):
        self.canvas_id = canvas_id

        self.subscription_topic = f"canvas/{canvas_id}/out"
        self.outgoing_topic = f"canvas/{canvas_id}/in"

        mqtt.client.subscribe_callback(
            self.subscription_topic + "/#",
            mqtt.mqtt_json_callback(self.handle_mqtt_response),
        )

        if logger is not None:
            self.log = logger
        else:
            logger = get_main_logger()

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
        self.on_disconnect = on_disconnect
        self.on_connect = on_connect
        self.connected = False

        self.aio = Canvas.AsyncCanvas(self, event_loop)

    def release(self):
        mqtt.client.unsubscribe_callback(self.subscription_topic + "/#")

    def handle_mqtt_response(self, topic, payload):
        tlen = len(self.subscription_topic) + 1
        topic = topic[tlen:]
        # self.log.debug(f"MQTT message received. canvas={self.canvas_id} topic={topic} payload={payload}")

        if topic == "result":
            # self.log.debug(f"Received result: {payload}")
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
            # dt = time.time() - payload["response_timestamp"]
            if "value" not in payload:
                return

            if self.connected == payload["value"]:
                return

            self.connected = payload["value"]

            if self.connected:
                if self.on_connect:
                    self.on_connect()
                self.aio._on_connect()
            else:
                if self.on_disconnect:
                    self.on_disconnect()
                self.aio._on_disconnect()

        elif topic == "image_onload":
            self.handle_image_onload(payload)

        elif topic == "image_onerror":
            self.handle_image_onerror(payload)

        elif topic == "video_loadedmetadata":
            self.handle_video_loadedmetadata(payload)

        elif topic == "video_error":
            self.handle_video_error(payload)

        elif topic == "video_on_update":
            self.handle_video_on_update(payload)

        elif topic == "video_on_ended":
            self.handle_video_on_ended(payload)

        elif topic == "tween_on_update":
            self.handle_tween_on_update(payload)

        elif topic == "tween_on_finish":
            self.handle_tween_on_finish(payload)

        elif topic == "window_on_resize":
            self.handle_window_on_resize(payload)

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

    def send_command(self, topic, payload, on_result=None, on_error=None, force=False):
        if not self.connected and not force:
            raise Exception(
                f"Sending command while canvas is not connected. topic={topic} payload={payload}"
            )

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
        handlers = self.image_handlers.get(payload["image_id"], None)
        if handlers is None:
            return

        handler = handlers.get("load", None)
        if handler is not None:
            handler(payload)
            with self.image_handlers_lock:
                del self.image_handlers[payload["image_id"]]["load"]

    def handle_image_onerror(self, payload):
        handlers = self.image_handlers.get(payload["image_id"], None)
        if handlers is not None:
            return
        handler = handlers.get("error", None)

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

    def handle_video_on_update(self, payload):
        handlers = self.video_handlers.get(payload["video_id"], None)
        if handlers is not None and handlers["on_update"] is not None:
            handlers["on_update"](payload)

    def handle_video_on_ended(self, payload):
        handlers = self.video_handlers.get(payload["video_id"], None)
        if handlers is not None and handlers["on_ended"] is not None:
            handlers["on_ended"](payload)

    def handle_video_error(self, payload):
        handlers = self.video_handlers.get(payload["video_id"], None)
        if handlers is None:
            return
        handler = handlers.get("error", None)

        if handler is not None:
            handler(payload)
            with self.video_handlers_lock:
                del self.video_handlers[payload["video_id"]]["error"]

    def handle_tween_on_update(self, payload):
        handlers = self.tween_handlers.get(payload["tween_id"], None)
        if handlers is not None and handlers["on_update"] is not None:
            payload["node"] = json.loads(payload["node"])
            handlers["on_update"](payload)

    def handle_tween_on_finish(self, payload):
        handlers = self.tween_handlers.get(payload["tween_id"], None)
        if handlers is not None and handlers["on_finish"] is not None:
            payload["node"] = json.loads(payload["node"])
            handlers["on_finish"](payload)

    def handle_window_on_resize(self, payload):
        pass  # TODO: add listeners for window resize

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

    def on(self, node_id, event_name, handler, on_result=None, on_error=None):
        with self.node_handlers_lock:
            self.node_handlers[(node_id, event_name)] = handler

        self.send_command(
            "on",
            {"node_id": node_id, "event_name": event_name},
            on_result=on_result,
            on_error=on_error,
        )

    def off(self, node_id, event_name, on_result=None, on_error=None):
        self.send_command(
            "off",
            {"node_id": node_id, "event_name": event_name},
            on_result=on_result,
            on_error=on_error,
        )

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
                "send_updates": on_update is not None,
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
        on_update=None,
        on_ended=None,
        on_result=None,
        on_error=None,
        **kwargs,
    ):
        with self.video_handlers_lock:
            self.video_handlers[video_id] = {
                "loadedmetadata": video_loadedmetadata,
                "on_update": on_update,
                "on_ended": on_ended,
                "error": video_error,
            }

        self.send_command(
            "load_video",
            {
                "video_id": video_id,
                "src": src,
                "send_updates": on_update is not None,
                **kwargs,
            },
            on_result=on_result,
            on_error=on_error,
        )

    def add_video(
        self,
        container_id: str,
        video_id: str,
        on_result=None,
        on_error=None,
        **kwargs,
    ):
        self.send_command(
            "add_video",
            {
                "container_id": container_id,
                "video_id": video_id,
                "node_config": kwargs,
            },
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

    def echo(self, on_result=None, on_error=None, force=True):
        self.send_command(
            "echo", {}, on_result=on_result, on_error=on_error, force=force
        )

    class AsyncCanvas:
        def __init__(self, canvas, event_loop=None) -> None:
            self.c: Canvas = canvas

            if event_loop is None:
                self._event_loop = asyncio.get_event_loop()
            else:
                self._event_loop = event_loop

            self._connect_future = self._event_loop.create_future()

            self.add = self.awaiting_func(self.c.add)
            self.node = self.awaiting_func(self.c.node)
            self.get_node = self.awaiting_func(self.c.get_node)
            self.on = self.awaiting_func(self.c.on)
            self.off = self.awaiting_func(self.c.off)
            self.reset = self.awaiting_func(self.c.reset)
            self.make_tween = self.awaiting_func(self.c.make_tween)
            self.remove_tween = self.awaiting_func(self.c.remove_tween)
            self.tween = self.awaiting_func(self.c.tween)
            self.play_tween = self.awaiting_func(self.c.play_tween)
            self.load_image = self.awaiting_func(self.c.load_image)
            self.remove_image = self.awaiting_func(self.c.remove_image)
            self.load_video = self.awaiting_func(self.c.load_video)
            self.add_video = self.awaiting_func(self.c.add_video)
            self.remove_video = self.awaiting_func(self.c.remove_video)
            self.play_video = self.awaiting_func(self.c.play_video)
            self.pause_video = self.awaiting_func(self.c.pause_video)
            self.video_set_props = self.awaiting_func(self.c.video_set_props)
            self.video_get_props = self.awaiting_func(self.c.video_get_props)
            self.echo = self.awaiting_func(self.c.echo)

        def awaiting_func(self, f):
            async def af(*args, **kwargs):
                return await self.c.wait(f, *args, **kwargs)

            return af

        async def connected(self):
            await self._connect_future

        def _on_connect(self):
            self._event_loop.call_soon_threadsafe(self._connect_future.set_result, True)

        def _on_disconnect(self):
            self._connect_future = self._event_loop.create_future()
