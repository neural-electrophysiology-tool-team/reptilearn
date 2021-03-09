import config
import state
import paho.mqtt.client as paho
import json
import threading
from dynamic_loading import load_module, find_subclass, reload_module


class ExperimentException(Exception):
    pass


state.update_state(["experiment"], {"is_running": False})
cur_experiment = None
state_dispatcher = state.Dispatcher()


# Initialize MQTT client
def on_mqtt_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info(
            f"MQTT connected successfully to {config.mqtt['host']}:{config.mqtt['port']}."
        )
    else:
        log.error(f"MQTT connection refused (rc code {rc}).")


mqttc = paho.Client()
mqttc.on_connect = on_mqtt_connect
mqtt_subscribed_topics = []


def mqtt_subscribe(topic, callback):
    mqtt_subscribed_topics.append(topic)
    mqttc.subscribe(topic)
    mqttc.message_callback_add(topic, callback)


def mqtt_unsubscribe(topic):
    if topic not in mqtt_subscribed_topics:
        return

    mqttc.unsubscribe(topic)
    mqttc.message_callback_remove(topic)
    mqtt_subscribed_topics.remove(topic)


def mqtt_unsubscribe_all():
    for topic in mqtt_subscribed_topics:
        mqttc.message_callback_remove(topic)
        mqttc.unsubscribe(topic)

    mqtt_subscribed_topics.clear()


def mqtt_json_callback(callback):
    def cb(client, userdata, message):
        payload = message.payload.decode("utf-8")
        if len(payload) == 0:
            payload = None
        if payload is not None:
            try:
                payload = json.loads(payload)
            except json.decoder.JSONDecodeError:
                pass

        callback(message.topic, payload)

    return cb


# experiment can be running or not. stop either because it ended or because we asked it to.
# should have cur block, trial and num_blocks num_trials
# the experiment should have a params dict that's overriden by block params.
# should have cur params with the right params for block (assoc cur block params into global params and put here)
# make it easy to make the flow time based.
def run(**params):
    if state.get_state_path(("experiment", "is_running")) is True:
        raise ExperimentException("Experiment is already running.")

    if cur_experiment is None:
        raise ExperimentException("Can't run experiment. No experiment was set.")

    state.update_state(("experiment", "params"), params)
    state.assoc_state(
        ["experiment"],
        {
            "is_running": True,
            "cur_block": 0,
            "cur_trial": 0,
        },
    )

    mqttc.loop_start()
    cur_experiment.run()


def end():
    if state.get_state_path(("experiment", "is_running")) is False:
        raise ExperimentException("Experiment is not running.")

    state.update_state(["experiment", "is_running"], False)

    cur_experiment.end()
    mqttc.loop_stop()


def set_phase(block, trial):
    # basically only works after running experiment because run resets cur phase.
    blocks = state.get_path(["experiment", "blocks"])
    if blocks == state.path_not_found:
        raise ExperimentException(
            "Bad experiment description. Blocks definition not found."
        )
    if len(blocks) <= block:
        raise ExperimentException(f"Block {block} is not defined.")

    if "num_trials" in blocks[block] and trial >= blocks[block]["num_trials"]:
        raise ExperimentException(f"Trial {trial} is out of range for block {block}.")

    state.assoc_state(["experiment"], {"cur_block": block, "cur_trial": trial})


def next_trial():
    cur_state = state.get_path(["experiment"])
    if "blocks" not in cur_state:
        raise ExperimentException(
            "Bad experiment description. Blocks definition not found."
        )

    cur_block_num = cur_state["cur_block"]
    cur_block = cur_state["blocks"][cur_block_num]

    cur_trial = cur_state["cur_trial"]

    num_trials = cur_block.get("num_trials")
    num_blocks = len(cur_state["blocks"])

    if num_trials is not None and cur_trial + 1 >= num_trials:
        # next block
        if cur_block_num + 1 < num_blocks:
            set_phase(cur_block_num + 1, 0)
        else:
            end()
    else:
        # next trial
        set_phase(cur_block_num, cur_trial + 1)


def load_experiments(experiments_dir=config.experiments_dir):
    experiments = {}
    experiment_pys = experiments_dir.glob("*.py")

    for py in experiment_pys:
        module, spec = load_module(py)
        cls = find_subclass(module, Experiment)
        if cls is not None:
            experiments[py.stem] = (cls, module, spec)

    return experiments


def init(logger):
    global log, experiments, state_dispatcher_thread
    log = logger
    experiments = load_experiments()
    log.info(f"Loaded {len(experiments)} experiment(s):")
    for e in experiments.keys():
        log.info(f"\t{e}")

    mqttc.connect(**config.mqtt)
    threading.Thread(target=state_dispatcher.listen).start()


def shutdown():
    state_dispatcher.stop()
    mqttc.disconnect()


def set_experiment(name):
    global cur_experiment

    if name == state.get_state_path(("experiment", "cur_experiment")):
        return
    
    if state.get_state_path(("experiment", "is_running")) is True:
        raise ExperimentException(
            "Can't set experiment while an experiment is running."
        )

    if name not in experiments.keys():
        raise ExperimentException(f"Unknown experiment name: {name}")

    if cur_experiment is not None:
        mqtt_unsubscribe_all()
        cur_experiment.release()
        
    spec = experiments[name][2]
    module = reload_module(spec)
    cls = find_subclass(module, Experiment)
    experiments[name] = (cls, module, spec)
    cur_experiment = cls(log)
    
    state.update_state(("experiment", "cur_experiment"), name)
    log.info(f"Loaded experiment {name}.")


class Experiment:
    def __init__(self, logger):
        self.log = logger
        self.setup()

    def run(self):
        pass

    def end(self):
        pass

    def setup(self):
        pass

    def release(self):
        pass
