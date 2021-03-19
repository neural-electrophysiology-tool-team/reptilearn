import experiment as exp
import mqtt


class YoloExperiment(exp.Experiment):
    def setup(self):
        self.prev_det = None

    def run(self, params):
        self.det_count = 0
        mqtt.client.subscribe_callback(
            "reptilearn/pogona_head_bbox",
            mqtt.mqtt_json_callback(self.on_yolo_detection),
        )
        self.log.info("YOLO Experiment is running.")

    def on_yolo_detection(self, topic, payload):
        # if self.det_count % 60 == 0:
        #    self.log.info(str(payload))
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

        if self.det_count % 60 == 0:
            exp.exp_state.update("last_known_position", payload)
            
        self.det_count += 1
        if det is not None and len(det) != 0:
            self.prev_det = det

    def end(self, params):
        mqtt.client.unsubscribe("reptilearn/pogona_head_bbox")
        exp.exp_state.remove("last_known_position")
