import multiprocessing as mp
from copy import deepcopy
import dict_transform as dt

_mgr = mp.Manager()
_ns = _mgr.Namespace()
_ns.state = _mgr.dict()
_did_update_events = _mgr.list()
_state_lock = _mgr.Lock()




def get():
    return deepcopy(_ns.state)


def get_path(path, default=None):
    return dt.get_path(get(), path, default)


def set(new_state):
    _ns.state = _mgr.dict(new_state)
    for e in _did_update_events:
        e.set()


def update(path, value):
    _state_lock.acquire()
    set(dt.update(get(), path, value))
    _state_lock.release()


def assoc(path, kvs):
    _state_lock.acquire()
    set(dt.assoc(get(), path, kvs))
    _state_lock.release()


def register_listener(on_update):
    did_update_event = _mgr.Event()
    stop_event = mp.Event()

    _did_update_events.append(did_update_event)
    old = get()

    def listen():
        nonlocal old
        try:
            while True:
                did_update_event.wait()
                if stop_event.is_set():
                    break
                did_update_event.clear()
                new = get()
                on_update(old, new)
                old = new
        except EOFError:
            pass

    def stop_listening():
        stop_event.set()
        did_update_event.set()

    return listen, stop_listening


def shutdown():
    _mgr.shutdown()


class Dispatcher():
    def __init__(self):
        super().__init__()
        self._dispatch_table = dict()

        def on_update(old, new):
            for path, on_update in self._dispatch_table.items():
                old_val = get_path(old, path, dt.path_not_found)
                new_val = get_path(new, path, dt.path_not_found)

                if not old_val == new_val:
                    on_update(old_val, new_val)

        self.listen, self.stop = register_listener(on_update)

    def add_callback(self, path, on_update):
        self._dispatch_table[path] = on_update

    def remove_callback(self, path):
        return self._dispatch_table.pop(path)
