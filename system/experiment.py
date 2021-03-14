import config
import state
import paho.mqtt.client as paho
import json
import threading
import sys
from dynamic_loading import load_module, find_subclass, reload_module


class ExperimentException(Exception):
    pass


state.update(["experiment"], {"is_running": False})
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
def run(params):
    if state.get_path(("experiment", "is_running")) is True:
        raise ExperimentException("Experiment is already running.")

    if cur_experiment is None:
        raise ExperimentException("Can't run experiment. No experiment was set.")

    state.update(("experiment", "params"), params)
    state.assoc(
        ["experiment"],
        {
            "is_running": True,
            "cur_block": 0,
            "cur_trial": 0,
        },
    )

    mqttc.loop_start()
    try:
        cur_experiment.run()
    except Exception:
        log.critical("Exception while calling running experiment:", exc_info=sys.exc_info())
        end()
        

def end():
    if state.get_path(("experiment", "is_running")) is False:
        raise ExperimentException("Experiment is not running.")

    state.update(["experiment", "is_running"], False)

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

    state.assoc(["experiment"], {"cur_block": block, "cur_trial": trial})


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
    experiment_specs = {}
    experiment_pys = experiments_dir.glob("*.py")

    for py in experiment_pys:
        module, spec = load_module(py)
        cls = find_subclass(module, Experiment)
        if cls is not None:
            experiment_specs[py.stem] = spec

    return experiment_specs


def init(logger):
    global log

    log = logger
    refresh_experiment_list()

    mqttc.connect(**config.mqtt)
    threading.Thread(target=state_dispatcher.listen).start()


def refresh_experiment_list():
    global experiment_specs
    experiment_specs = load_experiments()
    log.info(
        f"Loaded {len(experiment_specs)} experiment(s): {', '.join(experiment_specs.keys())}"
    )


def shutdown():
    if cur_experiment is not None:
        if state.get_path(("experiment", "is_running")):
            end()
        set_experiment(None)
        
    state_dispatcher.stop()
    mqttc.disconnect()


def set_experiment(name):
    global cur_experiment

    if state.get_path(("experiment", "is_running")) is True:
        raise ExperimentException(
            "Can't set experiment while an experiment is running."
        )

    if name not in experiment_specs.keys() and name is not None:
        raise ExperimentException(f"Unknown experiment name: {name}")

    if cur_experiment is not None:
        mqtt_unsubscribe_all()
        cur_experiment.release()

    if name is not None:
        spec = experiment_specs[name]
        module = reload_module(spec)
        cls = find_subclass(module, Experiment)
        cur_experiment = cls(log)

        log.info(f"Loaded experiment {name}.")
    else:
        cur_experiment = None
        log.info("Unloaded experiment.")

    state.update(("experiment", "cur_experiment"), name)


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
