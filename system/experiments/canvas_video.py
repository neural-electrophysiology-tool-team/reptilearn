import experiment as exp
from canvas import Canvas


class CanvasVideoExperiment(exp.Experiment):
    default_params = {
        "canvas_id": "1",
        "video_url": "http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "playback_rate": 1,
    }

    def on_video_update(self, payload):
        self.log.info(f"video update {payload}")

    def on_video_ended(self, payload):
        self.log.info(f"video ended {payload}")
        exp.next_block()

    def video_loadedmetadata(self, payload):
        self.log.info(f"Received video metadata: {payload}")
        metadata = payload["video"]
        w, h = metadata["width"], metadata["height"]
        self.canvas.add_video(
            "main",
            "vid",
            width=w // 4,  # w,
            height=h // 4,  # h,
            # x=(self.width - w) // 2,
            # y=(self.height - h) // 2,
            id="vid_node",
        )
        self.canvas.video_set_props("vid", playbackRate=exp.get_params()["playback_rate"])
        self.canvas.make_tween(
            "vid_pos",
            node_id="vid_node",
            x=self.width - w // 4,
            y=self.height - h // 4,
            duration=metadata["duration"],
        )
        self.canvas.make_tween(
            "vid_size",
            node_id="vid_node",
            width=w,
            height=h,
            duration=5,
            easing="BounceEaseIn"
        )

        self.canvas.play_tween("vid_pos")
        self.canvas.play_tween("vid_size")
        self.canvas.play_video("vid")

    def video_error(self, payload):
        self.log.info(f"Received video error: {payload}")

    async def run(self):
        self.canvas = Canvas(exp.get_params()["canvas_id"], on_disconnect=exp.stop_experiment)
        await self.canvas.aio.connected()
        stage = await self.canvas.aio.get_node("stage")
        self.width = stage["attrs"]["width"]
        self.height = stage["attrs"]["height"]

        await self.canvas.aio.reset()
        self.canvas.load_video(
            "vid",
            exp.get_params()["video_url"],
            muted=True,
            video_loadedmetadata=self.video_loadedmetadata,
            # on_update=self.on_video_update,
            on_ended=self.on_video_ended,
            video_error=self.video_error,
        )
        self.canvas.add(
            "stage",
            "Layer",
            id="main",
        )

    def run_trial(self):
        self.canvas.play_video("vid")

    async def end_trial(self):
        self.canvas.pause_video("vid")
        await self.canvas.aio.video_set_props("vid", currentTime=0)

    def end(self):
        self.canvas.remove_video("vid")
        self.canvas.node("vid_node", "destroy")
