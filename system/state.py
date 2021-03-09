import multiprocessing as mp
from copy import deepcopy

_mgr = mp.Manager()
_ns = _mgr.Namespace()
_ns.state = _mgr.dict()
_did_update_events = _mgr.list()
_state_lock = _mgr.Lock()


class _PathNotFound:
    pass


path_not_found = _PathNotFound()


def get_path(d, path, default=path_not_found):
    c = d
    for k in path:
        c = c.get(k, default)
        if c == default:
            break

    return c


def update(d, path, value):
    c = d
    for k in path[:-1]:
        c = c[k]
    c[path[-1]] = value
    return d


def assoc(d, path, kvs):
    c = d
    for k in path[:-1]:
        c = c[k]

    if not (isinstance(c, dict) or isinstance(c, list)):
        raise KeyError("assoc_state path does not point to a dictionary or list.")

    c[path[-1]] = dict(c[path[-1]], **kvs)
    return d


def get_state():
    return deepcopy(_ns.state)


def get_state_path(path, default=None):
    return get_path(get_state(), path, default)


def set_state(new_state):
    _ns.state = _mgr.dict(new_state)
    for e in _did_update_events:
        e.set()


def update_state(path, value):
    _state_lock.acquire()
    set_state(update(get_state(), path, value))
    _state_lock.release()


def assoc_state(path, kvs):
    _state_lock.acquire()
    set_state(assoc(get_state(), path, kvs))
    _state_lock.release()


def register_listener(on_update):
    did_update_event = _mgr.Event()
    stop_event = mp.Event()

    _did_update_events.append(did_update_event)
    old = get_state()

    def listen():
        nonlocal old
        try:
            while True:
                did_update_event.wait()
                if stop_event.is_set():
                    break
                did_update_event.clear()
                new = get_state()
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
                old_val = get_path(old, path, path_not_found)
                new_val = get_path(new, path, path_not_found)

                if not old_val == new_val:
                    on_update(old_val, new_val)

        self.listen, self.stop = register_listener(on_update)

    def add_callback(self, path, on_update):
        self._dispatch_table[path] = on_update

    def remove_callback(self, path):
        return self._dispatch_table.pop(path)
