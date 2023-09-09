import experiment as exp
import asyncio
from canvas import Canvas


class TiledCanvas(Canvas):
    def __init__(self, canvas_id, duration, offset=[0, 0], on_disconnect=None):
        super().__init__(canvas_id, on_disconnect=on_disconnect)
        self.offset = offset
        self.size = None
        self.on_done = None
        self.on_update = None
        self.duration = duration
        self.is_moving = False

    async def fetch_size(self):
        stage = await self.aio.get_node("stage")
        self.size = (stage["attrs"]["width"], stage["attrs"]["height"])
        return self.size

    async def make_background(self):
        await self.aio.add("stage", "Layer", id="back")
        self.node("back", "zIndex", 0)

        self.add(
            "back",
            "Rect",
            x=0,
            y=0,
            width=self.size[0],
            height=self.size[1],
            fill="black",
        )

        await self.aio.add("stage", "Layer", id="main")
        self.node("main", "zIndex", 1)

    async def make_shapes(self, radius):
        r = radius
        x = 0
        y = self.size[1] // 2 - r // 2

        await self.aio.add(
            "main",
            "Circle",
            x=x if self.offset[1] == 0 else x - r,
            y=y,
            radius=r,
            fill="white",
            stroke="gray",
            id="c",
            visible=False,
        )

        await self.aio.make_tween(
            "movement_tween",
            x=self.size[0] + r,
            easing="Linear",
            duration=self.duration,
            node_id="c",
            on_finish=self.done_moving,
            on_update=self.on_move_update,
        )

    def move(self, on_done=None, on_update=None):
        self.is_moving = True
        self.node("c", "show")
        self.play_tween("movement_tween")
        self.on_done = on_done
        self.on_update = on_update

    def on_move_update(self, resp):
        if self.on_update is not None:
            self.on_update(resp)

    def done_moving(self, resp):
        if self.on_done is not None:
            self.on_done(resp)
        self.is_moving = False

    async def destroy(self):
        await self.aio.node("main", "destroyChildren")


class MultiCanvasExperiment(exp.Experiment):
    default_params = {"canvas_ids": [[1, 2, 3]], "duration": 6, "radius": 30}

    def setup(self):
        self.canvases = None
        self.interval_task: asyncio.Task = None

    async def run_block(self):
        ids = exp.get_params()["canvas_ids"]
        duration = exp.get_params()["duration"]
        self.radius = exp.get_params()["radius"]
        self.canvases = []
        self.canvas_sizes = []

        for i, row in enumerate(ids):
            for j, id in enumerate(row):
                c = TiledCanvas(id, offset=[i, j], duration=duration / len(ids[i]), on_disconnect=exp.stop_experiment)
                self.log.info(f"Waiting for connection with canvas {id}")
                await c.aio.connected()
                await c.aio.reset()
                await c.fetch_size()
                await c.make_background()
                self.canvases.append(c)

    def on_done(self, resp, i):
        self.canvases[i].node("c", "hide")

        if i + 1 >= len(self.canvases):
            exp.next_trial()

    def maybe_next_canvas(self, resp, i):
        # collect timing data here

        if i != self.cur_canvas_idx:
            return
        if self.cur_canvas_idx + 1 >= len(self.canvases):
            return

        if "x" in resp["node"]["attrs"] and (
            resp["node"]["attrs"]["x"]
            > (self.canvases[self.cur_canvas_idx].size[0] - (self.radius // 2))
        ):
            self.cur_canvas_idx += 1
            self.move(i + 1)

    def move(self, i):
        if len(self.canvases) <= i:
            exp.stop_experiment()
            return

        self.log.info(f"Moving on canvas {self.canvases[i].canvas_id}")
        self.is_moving = True
        self.canvases[i].move(
            on_done=lambda resp: self.on_done(resp, i), on_update=lambda resp: self.maybe_next_canvas(resp, i)
        )

    async def run_trial(self):
        await asyncio.gather(*[c.make_shapes(self.radius) for c in self.canvases])
        self.cur_canvas_idx = 0
        self.move(0)

    async def end_trial(self):
        await asyncio.gather(*[c.destroy() for c in self.canvases])

    async def end_block(self):
        if self.canvases is not None:
            for c in self.canvases:
                c.release()
