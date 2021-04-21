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
        "exp_interval": 120,
        "trial_length": 40,
        "min_intersection": 0.5,
        "record_exp": True,
        "num_of_exp": 3,
        "led_duration": 2,
        "bypass_detection": True,
        "reward_detections": False,
        "reward_delay": 0,
        "record_overhead": 20,
        "winning_bbox": {'x1':0,'x2':200,'y1':0 ,'y2':300},
    }

    def setup(self):
        self.in_trial=False
        self.got_detection=False
        self.cancel_trials=None
        self.cancel_logic_trial=None
        self.cur_trial=None
        self.min_intersection=None


    def run(self, params):
        self.cur_trial = params['num_of_exp']
        mqtt.client.subscribe_callback("reptilearn/learn_exp/end",self.on_end)
        interval =  params["exp_interval"]
        self.cancel_trials = schedule.repeat(
            self.period_call, interval, params.get("num_of_exp", 1)
        )
        self.winning_bbox=params['winning_bbox']
        self.min_intersection=params['min_intersection']
        #exp.image_observers["head_bbox"].start_observing()

    def run_trial(self, params):
        self.in_trial=True
        if params.get("record_exp",True): video_record.start_record()

        led_d = params["led_duration"]
        self.log.info("Trial "+str(self.cur_trial)+" started " + str(datetime.datetime.now()))


        #Stupid temp trial: blinking twice and changing screen colors
        #blink twice
        arena.signal_led(True)
        schedule.once(lambda: arena.signal_led(False), led_d)
        schedule.once(lambda: arena.signal_led(True), led_d*2)
        schedule.once(lambda: arena.signal_led(False), led_d*3)

        for i in range(5):
            self.log.info("Color changed " + str(datetime.datetime.now()))
            mqtt.client.publish(topic="monitor/color",payload="random")
            time.sleep(1.5)

        # end of stupid temp trial

        #giving a reward if bypass_detection enabled
        if params["bypass_detection"] and params["reward_detections"]:
            self.dispatch_reward()
            self.end_logic_trial()
        else:#scheduling the end of trial
            self.cancel_logic_trial = schedule.once(self.end_logic_trial, params["trial_length"])

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
                if params["reward_detections"] and not params["bypass_detection"]: self.dispatch_reward()
                self.cancel_logic_trial() #got detection, canceling scheduled end
                self.end_logic_trial()


    def check_detection(self,locations):
        #returns the ratio between the intersection area and the
        #detected bbox area
        def get_intersection(rect_a,rect_b):
            dx = min(rect_a['x2'], rect_b['x2']) - max(rect_a['x1'], rect_b['x1'])
            dy = min(rect_a['y2'], rect_b['y2']) - max(rect_a['y1'], rect_b['y1'])
            if (dx >= 0) and (dy >= 0): return dx * dy


        inter_area= get_intersection(self.winning_bbox,locations)
        detected_area=(locations['x2']-locations['x1'])*(locations['y2']-locations['y2'])
        if inter_area==None or inter_area/detected_area < self.min_intersection:
            return False
        else:
            return True

    def end_logic_trial(self):
        if self.in_trial and not self.got_detection:
            self.log.info("Logic trial ended, failure")
        elif self.in_trial and self.got_detection:
            self.log.info("Logic trial ended, success")
        else:
            self.log.info("Logic trial ended")
        if params.get("record_exp",True): schedule.once(lambda: video_record.stop_record(), params.get("record_overhead", 0))
        self.in_trial=False
        self.got_detection=False



    def end_trial(self,params):
        if self.in_trial:
            self.log.info("Logic trial wasnt finished!")
            if params.get("record_exp",True): schedule.once(lambda: video_record.stop_record(), params.get("record_overhead", 0))
            self.in_trial = False
            self.got_detection = False
        self.cur_trial = self.cur_trial - 1


    def dispatch_reward(self):
        schedule.once(lambda: arena.dispense_reward(),params.get("reward_delay", 0))


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
            self.cancel_logic_trial()
            self.end_logic_trial()




