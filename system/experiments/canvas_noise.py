import experiment as exp
from canvas import Canvas


class CanvasNoiseExperiment(exp.Experiment):
    default_params = {"canvas_id": "1"}

    async def run_block(self):
        self.canvas = Canvas(exp.get_params()["canvas_id"], on_disconnect=exp.stop_experiment)
        self.log.info("Connecting...")
        await self.canvas.aio.connected()
        self.log.info("Done connecting.")
        await self.canvas.aio.reset()
        await self.canvas.aio.add("stage", "Layer", id="main")

        stage = await self.canvas.aio.get_node("stage")
        self.width = stage["attrs"]["width"]
        self.height = stage["attrs"]["height"]
        rad = self.width // 6

        await self.canvas.aio.add(
            "main",
            "Circle",
            x=self.width // 2,
            y=self.height // 2,
            radius=rad,
            fill="red",
            id="shape",
            filters=["Noise", "Mask"],
            threshold=255,
            noise=0,
        )
        self.canvas.make_tween("noise_tween", noise=1.0, node_id="shape", duration=10, on_finish=lambda resp: exp.next_block())
        self.canvas.make_tween("mask_tween", threshold=150, node_id="shape", duration=10)
        self.canvas.node("shape", "cache")
        self.canvas.play_tween("noise_tween")
        self.canvas.play_tween("mask_tween")

    async def end_block(self):
        await self.canvas.aio.reset()
