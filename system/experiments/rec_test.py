import schedule
import experiment as exp
from experiment import exp_state
from state import state
import video_record


class Experiment(exp.Experiment):
    default_params = {"record_video": True, "take_image": True, "sources": None}

    def run(self, params):
        self.prev_prefix = state["video_record", "filename_prefix"]

    def run_block(self, params):
        sources = params["sources"]

        if params["record_video"]:
            state["video_record", "filename_prefix"] = f"block{exp_state['cur_block']}"
            video_record.stop_record()

            def delayed_rec():
                if params["take_image"]:
                    video_record.save_image(sources)
                video_record.start_record(sources)

            self.cancel_sched = schedule.once(delayed_rec, 1)
        elif params["take_image"]:
            video_record.save_image(sources)
        else:
            state["video_record", "filename_prefix"] = self.prev_prefix

    def end(self, params):
        try:
            self.cancel_sched()
        except AttributeError:
            pass

        state["video_record", "filename_prefix"] = self.prev_prefix
        video_record.stop_record()
