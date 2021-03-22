import schedule
import experiment as exp
from experiment import exp_state
from state import state
import video_record


class Experiment(exp.Experiment):
    default_params = {
        "record_video": True,
        "sources": None
    }

    def run(self, params):
        self.prev_prefix = state["video_record", "filename_prefix"]
        
    def run_block(self, params):
        if params["record_video"]:
            state["video_record", "filename_prefix"] = f"block{exp_state['cur_block']}"
            video_record.stop_record()
            schedule.once((lambda: video_record.start_record(params["sources"])), 1)
        else:
            state["video_record", "filename_prefix"] = self.prev_prefix
            
    def end(self, params):
        state["video_record", "filename_prefix"] = self.prev_prefix
        video_record.stop_record()
