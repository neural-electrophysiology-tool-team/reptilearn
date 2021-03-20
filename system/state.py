import multiprocessing as mp
from copy import deepcopy
import dicttools as dt

_mgr = mp.Manager()
_ns = _mgr.Namespace()
_ns.state = _mgr.dict()
_did_update_events = _mgr.list()
_state_lock = _mgr.Lock()


def get():
    return deepcopy(_ns.state)


def set(new_state):
    _ns.state = _mgr.dict(new_state)
    for e in _did_update_events:
        e.set()


def _mutating_fn(f):
    def mutating(*args, **kwargs):
        with _state_lock:
            set(f(get(), *args, **kwargs))

    return mutating


def _querying_fn(f):
    def querying(*args, **kwargs):
        return f(get(), *args, **kwargs)

    return querying


getitem = _querying_fn(dt.getitem)
setitem = _mutating_fn(dt.setitem)
update = _mutating_fn(dt.update)
remove = _mutating_fn(dt.remove)
append = _mutating_fn(dt.append)
contains = _querying_fn(dt.contains)
exists = _querying_fn(dt.exists)


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


class StateDispatcher:
    def __init__(self):
        super().__init__()
        self._dispatch_table = dict()

        def on_update(old, new):
            for path, on_update in self._dispatch_table.items():
                old_val = dt.getitem(old, path)
                new_val = dt.getitem(new, path)

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
        self.get = partial_path_fn(getitem, path)
        self.setitem = partial_path_fn(setitem, path)
        self.update = partial_path_fn(update, path)
        self.remove = partial_path_fn(remove, path)
        self.append = partial_path_fn(append, path)
        self.contains = partial_path_fn(contains, path)
        self.exists = partial_path_fn(exists, path)

    def get_self(self, *args, **kwargs):
        if self.path == ():
            return get(*args, **kwargs)
        else:
            return getitem(self.path, *args, **kwargs)

    def set_self(self, value):
        if self.path == ():
            return set(value)
        else:
            return setitem(self.path, value)

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

    def __getitem__(self, path):
        return self.get(path)

    def __setitem__(self, path, v):
        return self.setitem(path, v)

    def __str__(self):
        return str(self.get_self())

    def __contains__(self, k):
        if type(k) is tuple:
            if len(k) > 1:
                return self.exists(self.path + k)
            else:
                k = k[0]

        return contains(self.path, k)


state = Cursor(())
