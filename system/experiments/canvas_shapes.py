import experiment as exp
from canvas import Canvas
import random
import asyncio


class RandomShapes(Canvas):
    def __init__(self, canvas_id, n_nodes, logger, shape="Circle"):
        super().__init__(canvas_id, on_connect=self.on_connect, on_disconnect=self.on_disconnect)
        # self.interval = interval
        self.n_nodes = n_nodes
        self.nodes = None
        self.shape = shape
        self.last_tween = None
        self.log = logger

    async def make_background(self):
        await self.aio.add("stage", "Layer", id="back")
        self.node("back", "zIndex", 0)

        self.add(
            "back", "Rect", x=0, y=0, width=self.width, height=self.height, fill="black"
        )

        await self.aio.add("stage", "Layer", id="main")
        self.node("main", "zIndex", 1)

    async def make_shape(self, i):
        done_fut = asyncio.Future()

        color = random.choice(["red", "blue", "green", "yellow", "magenta", "cyan"])
        r = random.randint(self.width // 40, 2 * self.width // 40)
        x = random.randint(r, self.width - r)
        y = random.randint(r, self.height - r)
        vx, vy = (self.width / 192) * (random.random() * 2 - 1), (self.height / 192) * (random.random() * 2 - 1)
        node = {"pos": [x, y], "vel": [vx, vy], "rad": r}
        self.nodes.append(node)

        if self.shape != "Image":
            if self.shape == "Circle":
                await self.aio.add(
                    "main",
                    "Circle",
                    x=x,
                    y=y,
                    radius=r,
                    fill=color,
                    id=f"c{i}",
                )
            elif self.shape == "Rect":
                await self.aio.add(
                    "main",
                    "Rect",
                    x=x,
                    y=y,
                    offsetX=r,
                    offsetY=r,
                    width=2 * r,
                    height=2 * r,
                    fill=color,
                    id=f"c{i}",
                )

            self.node(f"c{i}", "cache")
            self.on(f"c{i}", "mousedown", self.on_mousedown)
            self.on(f"c{i}", "mouseup", self.on_mouseup)
            self.make_tween(
                f"tween_c{i}_scale",
                scaleX=2,
                scaleY=2,
                easing="EaseOut",
                duration=1,
                fill="gray",
                node_id=f"c{i}",
            )
            done_fut.set_result(1)

        elif self.shape == "Image":
            def image_loaded(_):
                async def _async_image_loaded():
                    await self.aio.add(
                        "main",
                        "Image",
                        image_id=f"img_{i}",
                        x=x,
                        y=y,
                        offsetX=r,
                        offsetY=r,
                        width=2 * r,
                        height=2 * r,
                        id=f"c{i}",
                    )
                    self.node(f"c{i}", "cache")
                    self.on(f"c{i}", "mousedown", self.on_mousedown)
                    self.on(f"c{i}", "mouseup", self.on_mouseup)
                    self.make_tween(
                        f"tween_c{i}_scale",
                        scaleX=2,
                        scaleY=2,
                        easing="EaseOut",
                        duration=1,
                        fill="gray",
                        node_id=f"c{i}",
                    )

                    done_fut.set_result(1)
                exp._run_coroutine(_async_image_loaded())

            self.load_image(
                f"img_{i}",
                f"https://placekitten.com/{2*r}/{2*r}",
                image_onload=image_loaded,
                image_onerror=lambda payload: self.log.error(payload),
            )

        await done_fut

    async def make_shapes(self):
        self.nodes = []
        await asyncio.gather(*[self.make_shape(i) for i in range(self.n_nodes)])

        self.on("stage", "mouseup", self.on_mouseup)

    async def setup(self):
        await self.aio.reset()

        stage = await self.aio.get_node("stage")

        self.width = stage["attrs"]["width"]
        self.height = stage["attrs"]["height"]
        self.log.info(f"width={self.width} height={self.height}")

        await self.make_background()

    def on_connect(self):
        self.log.info(f"Canvas {self.canvas_id} connected")

    def on_disconnect(self):
        self.log.info(f"Canvas {self.canvas_id} disconnected")
        exp.stop_experiment()

    def update_node(self, i, node):
        self.nodes[i] = node
        x, y = node["pos"]
        self.node(f"c{i}", "absolutePosition", {"x": x, "y": y})

    def update(self):
        if not self.connected:
            return

        if not self.nodes or len(self.nodes) == 0:
            return

        for i, node in enumerate(self.nodes):
            x, y = node["pos"][0] + node["vel"][0], node["pos"][1] + node["vel"][1]
            r = node["rad"]
            vx, vy = node["vel"][0], node["vel"][1]
            if x >= (self.width - r) or x < r:
                vx = -vx

            if y >= (self.height - r) or y < r:
                vy = -vy

            self.update_node(
                i,
                {"pos": [x, y], "vel": [vx, vy], "rad": r},
            )

    def on_mousedown(self, event):
        target_id = event["event"]["target"]["attrs"]["id"]
        tween_id = f"tween_{target_id}_scale"
        self.play_tween(tween_id)
        self.last_tween = tween_id

    def on_mouseup(self, event):
        if self.last_tween is not None:
            self.tween(self.last_tween, "reverse")
            self.last_tween = None

    async def destroy(self):
        await self.aio.node("main", "destroyChildren")
        self.nodes = None


class CanvasShapesExperiment(exp.Experiment):
    default_params = {"fps": 30, "n_nodes": 50, "canvas_ids": [1, 2], "shape": "Circle"}

    def setup(self):
        self.canvases = None
        self.interval_task: asyncio.Task = None

    async def run_block(self):
        ids = exp.get_params()["canvas_ids"]
        n_nodes = exp.get_params()["n_nodes"]
        shape = exp.get_params()["shape"]

        self.canvases = []
        for id in ids:
            c = RandomShapes(id, n_nodes, self.log, shape)
            self.canvases.append(c)

        self.log.info("Waiting for connection...")
        await asyncio.gather(*[c.aio.connected() for c in self.canvases])
        await asyncio.gather(*[c.setup() for c in self.canvases])
        self.log.info("Done setting up")

    async def run_trial(self):
        await asyncio.gather(*[c.make_shapes() for c in self.canvases])

        self.interval_task = asyncio.create_task(
            self.update(1 / exp.get_params()["fps"])
        )

    async def end_trial(self):
        if self.interval_task is not None:
            self.interval_task.cancel()

        await asyncio.gather(*[c.destroy() for c in self.canvases if c.connected])

    async def end_block(self):
        if self.canvases is not None:
            for c in self.canvases:
                c.release()

    async def update(self, interval):
        while True:
            for c in self.canvases:
                c.update()

            await asyncio.sleep(interval)
