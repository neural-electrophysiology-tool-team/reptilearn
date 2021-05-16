import experiment as exp
import mqtt
import data_log


class YoloExperiment(exp.Experiment):
    def setup(self):
        self.prev_det = None
        
    def run(self, params):
        self.first_detection = True
        self.yolo_log = data_log.QueuedDataLogger(
            columns=[
                ("time", "timestamptz not null"),
                ("x1", "double precision"),
                ("y1", "double precision"),
                ("x2", "double precision"),
                ("y2", "double precision"),
                ("confidence", "double precision"),
            ],
            csv_path=exp.exp_state["data_dir"] / "head_bbox.csv",
            table_name="bbox_position",
        )
        self.yolo_log.start()

        self.det_count = 0
        """
        mqtt.client.subscribe_callback(
            "reptilearn/pogona_head_bbox",
            mqtt.mqtt_json_callback(self.on_yolo_detection),
        )
        """
        yolo = exp.image_observers["head_bbox"]
        yolo.on_detection = self.on_yolo_detection
        yolo.start_observing()
        
        exp.exp_state["last_position"] = None

        self.log.info("YOLO Experiment is running.")

    def on_yolo_detection(self, payload):
        if self.first_detection:
            self.first_detection = False
            self.log.info("Received detection from YOLO observer")

        det = payload["detection"]
        if (
            det is not None
            and self.prev_det is not None
            and len(det) != 0
            and len(self.prev_det) != 0
        ):
            if det[1] < 500 and self.prev_det[1] >= 500:
                self.log.info("Pogona moved to upper half " + str(det))
            elif det[1] > 500 and self.prev_det[1] <= 500:
                self.log.info("Pogona moved to lower half " + str(det))

        if det is not None and len(det) != 0:
            self.yolo_log.log((payload["image_timestamp"], *det))
        else:
            self.yolo_log.log((payload["image_timestamp"], *((None,) * 5)))

        if self.det_count % 60 == 0:
            exp.exp_state["last_position"] = payload

        self.det_count += 1
        if det is not None and len(det) != 0:
            self.prev_det = det

    def end(self, params):
        #mqtt.client.unsubscribe_callback("reptilearn/pogona_head_bbox")
        exp.image_observers["head_bbox"].stop_observing()
        exp.exp_state.delete("last_position")
        self.yolo_log.stop()
