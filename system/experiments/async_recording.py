import experiment as exp
import video_system
import schedule


class AsyncRecordingExperiment(exp.Experiment):
    default_params = {
        "record_groups": {},
        "split_rec_every": 12 * 60 * 60,
        "split_gap": 1,
    }

    def setup(self):
        self.cancel_start_scheds = {}
        self.cancel_stop_scheds = {}

    def run(self):
        groups = exp.get_params()["record_groups"]

        for group_name in groups.keys():
            exp.session_state[f"recording_{group_name}"] = False

        self.update_actions()

    def end(self):
        groups = exp.get_params()["record_groups"]

        self.actions = {}
        exp.refresh_actions()

        for group_name in groups.keys():
            exp.session_state.delete(f"recording_{group_name}")
            self.stop_record_group(group_name)
            self.cancel_group_scheds(group_name)

    def toggle_rec_group(self, group_name):
        if self.is_recording(group_name):
            self.stop_record_group(group_name)
            self.cancel_group_scheds(group_name)
        else:
            self.start_record_group(group_name)

        self.update_actions()

    def start_record_group(self, group_name):
        group = exp.get_params()["record_groups"][group_name]
        split_every = exp.get_params()["split_rec_every"]
        split_gap = exp.get_params()["split_gap"]

        exp.session_state[f"recording_{group_name}"] = True
        for src_id in group:
            video_system.video_writers[src_id].start_observing()

        self.cancel_stop_scheds[group_name] = schedule.once(
            lambda: self.stop_record_group(group_name), split_every
        )
        self.cancel_start_scheds[group_name] = schedule.once(
            lambda: self.start_record_group(group_name), split_every + split_gap
        )

    def stop_record_group(self, group_name):
        group = exp.get_params()["record_groups"][group_name]

        exp.session_state[f"recording_{group_name}"] = False
        for src_id in group:
            video_system.video_writers[src_id].stop_observing()

    def is_recording(self, group_name):
        return exp.session_state[f"recording_{group_name}"]

    def cancel_group_scheds(self, group_name):
        if group_name in self.cancel_start_scheds:
            self.cancel_start_scheds[group_name]()
            del self.cancel_start_scheds[group_name]
        if group_name in self.cancel_stop_scheds:
            self.cancel_stop_scheds[group_name]()
            del self.cancel_stop_scheds[group_name]

    def update_actions(self):
        groups = exp.get_params()["record_groups"]

        self.actions = {}

        for group_name in groups.keys():
            self.actions[
                f"{'Stop' if self.is_recording(group_name) else 'Start'} recording {group_name}"
            ] = {"run": self.group_toggler(group_name)}

        exp.refresh_actions()

    def group_toggler(self, group_name):
        def fn():
            self.toggle_rec_group(group_name)

        return fn
