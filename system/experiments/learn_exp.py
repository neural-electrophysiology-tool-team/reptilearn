import experiment as exp
import mqtt
import data_log
import arena
import time
import datetime
import schedule
import video_record

class LearnExp(exp.Experiment):
    default_params = {
        "exp_interval": 60,
        "record_exp": True,
        "num_of_exp": 3,
        "led_duration": 2,
        "bypass_detection": True,
        "reward_detections": False,
        "reward_delay": 0,
        "record_overhead": 20,
        "winning_bbox": [0,0,300,300],
        "bbox_tolerance": 40,
    }

    def setup(self):
        self.in_trial=False
        self.got_detection=False
        self.cancel_trials=None
        self.cur_trial=None


    def run(self, params):
        self.cur_trial = params['num_of_exp']
        mqtt.client.subscribe_callback("reptilearn/learn_exp/end",self.on_end)
        interval=  params["exp_interval"]
        self.cancel_trials = schedule.repeat(
            self.period_call, interval, params.get("num_of_exp", True)
        )
        self.winning_bbox=params['winning_bbox']
        self.tolerance = params['bbox_tolerance']
        #exp.image_observers["head_bbox"].start_observing()

    def run_trial(self, params):
        self.in_trial=True
        video_record.start_record()

        led_d = params["led_duration"]
        self.log.info("Trial "+str(self.cur_trial)+" started " + str(datetime.datetime.now()))
        #blink twice
        arena.signal_led(True)
        schedule.once(lambda: arena.signal_led(False), led_d)
        schedule.once(lambda: arena.signal_led(True), led_d*2)
        schedule.once(lambda: arena.signal_led(False), led_d*3)

        for i in range(5):
            self.log.info("Color changed " + str(datetime.datetime.now()))
            mqtt.client.publish(topic="monitor/color",payload="random")
            time.sleep(1.5)

        if params["bypass_detection"] and params["reward_detections"]:
            self.dispatch_reward()
            self.end_logic_trial()

        self.log.info("run_trial finished")


    def on_yolo_detection(self, topic, payload):
        det = payload["detection"]
        if (
            det is not None
            and self.prev_det is not None
            and len(det) != 0
            and len(self.prev_det) != 0
            ) and self.check_detection(det):
            self.log.info("YOLO success at "+str(det))
            if self.in_trial:
                self.got_detection=True
                self.end_logic_trial()


    def check_detection(self,locations):
        res= True
        for i in range(4):
            if abs(locations[i]-self.winning_bbox[i])>self.tolerance: res=False

        return res


    def end_logic_trial(self):
        if self.in_trial and not self.got_detection:
            self.log.info("Logic trial ended, failure")
        elif self.in_trial and self.got_detection:
            self.log.info("Logic trial ended, success")
        else:
            self.log.info("Logic trial ended")
        video_record.stop_record()
        self.in_trial=False
        self.got_detection=False



    def end_trial(self,params):
        if self.in_trial:
            self.log.info("Logic trial wasnt finished!")
            video_record.stop_record()
            self.in_trial = False
            self.got_detection = False
        self.cur_trial = self.cur_trial - 1


    def dispatch_reward(self):
        schedule.once(lambda: arena.dispense_reward(),params['reward_delay'])


    def end(self, params):
        mqtt.client.publish(topic="monitor/color", payload="black")
        #exp.image_observers["head_bbox"].stop_observing()
        mqtt.client.unsubscribe("reptilearn/learn_exp/end")
        self.log.info("exp ended")

    def period_call(self):
        exp.next_trial()

    def on_end(self,client,userdata,message):
        self.log.info("on_end was called")
        if self.in_trial:
            self.log.info("ending logical trial")
            self.end_logic_trial()




