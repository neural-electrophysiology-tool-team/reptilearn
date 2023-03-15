import experiment as exp
from experiment import session_state
import arena
import functools


class StackedFeeders(exp.Experiment):
    default_params = {
        "feeders": {
            "Left Feeders": ["Bottom Left Feeder", "Top Left Feeder"],
            "Right Feeders": ["Bottom Right Feeder", "Top Right Feeder"],
        },
        "feeder_capacity": 15,
    }

    def dispense_reward(self, feeder_name, data={}):
        reward_count = session_state[feeder_name, "reward_count"] + 1
        feeder_interfaces = exp.get_params()["feeders"][feeder_name]
        feeder_capacity = exp.get_params()["feeder_capacity"]
        max_reward = feeder_capacity * len(feeder_interfaces)

        self.log.info(f"{reward_count}, {feeder_name}, {feeder_interfaces}, {max_reward}")

        if reward_count <= max_reward:
            feeder_number = reward_count // (feeder_capacity + 1)
            feeder_interface = feeder_interfaces[feeder_number]

            exp.event_logger.log(
                "dispensing_reward",
                {
                    **data,                    
                    **{
                        "num": reward_count,
                        "feeder": feeder_name,
                        "feeder_interface": feeder_interface
                    },
                },
            )

            self.log.info(f"Dispensing reward #{reward_count} from {feeder_interface}")
            arena.run_command("dispense", feeder_interface, None, False)
            session_state[feeder_name, "reward_count"] = reward_count

            if reward_count == max_reward:
                session_state[feeder_name, "out_of_rewards"] = True
                self.log.info(f"Out of rewards in feeder {feeder_name}!")
                exp.event_logger.log("out_of_rewards", {"feeder_name": feeder_name})

        else:
            exp.event_logger.log(
                "cannot_dispense_reward",
                {
                    **data,
                    "feeder": feeder_name,
                },
            )

    def reset_rewards_count(self):
        feeder_interfaces = exp.get_params()["feeders"]
        session_state.update(
            (),
            {feeder_name: {
                "reward_count": 0,
                "out_of_rewards": False,
            } for feeder_name in feeder_interfaces.keys()}
        )

        exp.event_logger.log(
            "rewards_available",
            {},
        )

    def setup(self):
        self.actions["Reset rewards"] = {"run": self.reset_rewards_count}

    def run(self):
        if "rewards_count" not in exp.session_state:
            self.reset_rewards_count()

        for feeder_name in exp.get_params()["feeders"].keys():
            self.log.info(f"name {feeder_name}")
            self.actions[f"Dispense {feeder_name}"] = {"run": functools.partial(self.dispense_reward, feeder_name)}

        exp.refresh_actions()
