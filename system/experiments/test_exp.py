import random
import experiment as exp
from experiment import exp_state
import arena
import schedule
import mqtt
from state import state


class TestExperiment(exp.Experiment):
    default_params = {
        "run_msg": "TestExperiment is running",
        "end_msg": "TestExperiment has ended",
        "blink_dur": 1.0,
    }

    default_blocks = [
        {"run_msg": f"block {i}", "end_msg": f"end block {i}"} for i in range(5)
    ]

    def run_trial(self, params):
        self.log.info("new trial")

    def run_block(self, params):
        self.log.info(params["run_msg"])
        arena.signal_led(True)
        if "blink_dur" in params:
            schedule.once(lambda: arena.signal_led(False), params["blink_dur"])

    def run(self, params):
        self.log.info(params["run_msg"])
        state.add_callback(
            ("arena", "sensors"),
            lambda o, n: self.log.info(f"Sensors update: {o} -> {n}"),
        )

        exp_state.add_callback(
            "test_cb", lambda o, n: self.log.info(f"test: {o} -> {n}")
        )

        mqtt.client.subscribe_callback(
            "arena/ttl_trigger/start",
            mqtt.mqtt_json_callback(lambda t, p: self.log.info(f"{t} {p}")),
        )

        def update_test_cb():
            exp_state["test_cb"] = random.randint(0, 100)

        #self.cancel_seq = schedule.sequence(
        #    update_test_cb, [2, 2, 5, 2, 2, 3], repeats=4
        #)
        arena.sensors_poll()
        arena.sensors_set_interval(10)

    def end_block(self, params):
        self.log.info(params["end_msg"])

    def end(self, params):
        self.log.info(params["end_msg"])
        state.remove_callback(("arena", "sensors"))
        exp_state.remove_callback("test_cb")
        arena.sensors_set_interval(60)
        #if self.cancel_seq:
        #    self.cancel_seq()
        mqtt.client.unsubscribe_callback("arena/ttl_trigger/start")
