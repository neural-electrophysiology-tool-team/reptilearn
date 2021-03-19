import multiprocessing as mp
from copy import deepcopy
import dicttools as dt

_mgr = mp.Manager()
_ns = _mgr.Namespace()
_ns.state = _mgr.dict()
_did_update_events = _mgr.list()
_state_lock = _mgr.Lock()

path_not_found = dt.path_not_found


def mutating_fn(f):
    def mutating(*args, **kwargs):
        with _state_lock:
            set(f(get(), *args, **kwargs))

    return mutating


def get():
    return deepcopy(_ns.state)


def get_path(path, default=path_not_found):
    return dt.get_path(get(), path, default)


def set(new_state):
    _ns.state = _mgr.dict(new_state)
    for e in _did_update_events:
        e.set()


update = mutating_fn(dt.update)
assoc = mutating_fn(dt.assoc)
remove = mutating_fn(dt.remove)


def contains(path, v):
    return dt.contains(get(), path, v)


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


class Dispatcher:
    def __init__(self):
        super().__init__()
        self._dispatch_table = dict()

        def on_update(old, new):
            for path, on_update in self._dispatch_table.items():
                old_val = dt.get_path(old, path, dt.path_not_found)
                new_val = dt.get_path(new, path, dt.path_not_found)

                if not old_val == new_val:
                    on_update(old_val, new_val)

        self.listen, self.stop = register_listener(on_update)

    def add_callback(self, path, on_update):
        self._dispatch_table[path] = on_update

    def remove_callback(self, path):
        return self._dispatch_table.pop(path)


def partial_path_fn(f, path_prefix):
    def fn(path, *args, **kwargs):
        if isinstance(path, str):
            path = (path,)

        return f(path_prefix + path, *args, **kwargs)

    return fn


class Cursor:
    def __init__(self, path):
        if isinstance(path, str):
            path = (path,)

        self.path = path
        self.get_path = partial_path_fn(get_path, path)
        self.update = partial_path_fn(update, path)
        self.assoc = partial_path_fn(assoc, path)
        self.remove = partial_path_fn(remove, path)
        self.contains = partial_path_fn(contains, path)

    def get(self, *args, **kwargs):
        return get_path(self.path, *args, **kwargs)

    def set(self, value):
        return update(self.path, value)

    def parent(self):
        if len(self.path) == 0:
            raise KeyError(f"path {self.path} has no parent.")

        return Cursor(self.path[:-1])

    def absolute_path(self, rel_path):
        if isinstance(rel_path, str):
            rel_path = (rel_path,)

        return self.path + rel_path

    def get_cursor(self, path):
        return Cursor(self.absolute_path(path))

    def exists(self):
        v = get_path(self.path)
        return v is not path_not_found

    def __getitem__(self, path):
        return self.get_path(path)
