import state
import mqtt
import video_record
import experiment as exp


class TestExperiment(exp.Experiment):
    def setup(self):
        exp.state_dispatcher.add_callback(("experiment", "cur_trial"), lambda o, n: print("cur_trial:", n))
        exp.mqtt_subscribe("#", exp.mqtt_json_callback(print))
        
    def run(self):
        self.log.info("TestExperiment is running")
        exp.mqttc.publish("reptilearn/testexp/starting")
        
    def end(self):
        self.log.info("TestExperiment has ended")
        exp.mqttc.publish("reptilearn/testexp/ended")

    def release(self):
        exp.state_dispatcher.remove_callback(("experiment", "cur_trial"))
