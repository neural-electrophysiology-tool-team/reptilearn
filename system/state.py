"""
Synchronized multiprocessing state management.
Author: Tal Eisenberg, 2021

This module provides a synchronized global state dictionary implemented using python's
multiprocessing.Manager. Any process can access and mutate the state using Cursor objects.
The register_listener() function and StateDispatcher class provide a listening mechanism
for state updates. The former allows to register a function that will be called on every
state update, while the latter allows registering listeners for state changes in specific
paths.

State values can be accessed using path notation - a string key or a tuple of string keys
and int indices. The path points to a nested position in the state tree. For example,
the path ("a", 0, "b") points to the "b" key of the 1st element of the list under the "a" key.

The state module attribute is a cursor pointing to the root path (the empty tuple),
and should be the entry point for using this module.

The simplest way to listen for updates to a specific state path, is by using the
Cursor.add_callback and Cursor.remove_callback functions.

Note: the root cursor uses a StateDispatcher that runs as a main process thread, therefore callbacks
registered with this dispatcher will also run on the main process. Any cursor derived from the root
cursor using the Cursor.get_cursor() method will inherit this state dispatcher. To run update callbacks
on other processes, create a new StateDispatcher instance and run it in the desired process.

See the docs for Cursor and the dicttools module for more information.
"""

import multiprocessing as mp
from copy import deepcopy
import dicttools as dt
import threading

# The global state is a dict managed by _mgr stored in namespace _ns
_mgr = None
_ns = None

# A list of mp.Event objects. These events are set whenever the state is updated.
_did_update_events = None

# Used for synchronized read and writes from the state.
_state_lock = None

# A state dispatcher running in a thread on the main process
_dispatcher = None


def init():
    global _mgr, _ns, _did_update_events, _state_lock, _dispatcher
    _mgr = mp.Manager()
    _ns = _mgr.Namespace()
    _ns.state = _mgr.dict()

    _did_update_events = _mgr.list()

    _state_lock = _mgr.Lock()

    _dispatcher = StateDispatcher()
    threading.Thread(target=_dispatcher.listen).start()
    state.state_dispatcher = _dispatcher


def shutdown():
    _dispatcher.stop()
    _mgr.shutdown()


def get():
    """Return a deep copy of the state"""
    return deepcopy(_ns.state)


def set(new_state):
    """Replace the current state dict with the new_state dict. Trigger update events."""
    _ns.state = _mgr.dict(new_state)
    for e in _did_update_events:
        e.set()


def _mutating_fn(f):
    """
    Return a function that safely mutates the state using function f. f receives a deep copy of the state, with
    additional args passed to the mutating function. The value it returns replaces the current state dict.
    """

    def mutating(*args, **kwargs):
        with _state_lock:
            set(f(get(), *args, **kwargs))

    return mutating


def _querying_fn(f):
    """
    Return a function that queries the state using function f. f receives a deep copy of the state, with
    additional args passed to the querying function. The return value of is returned.
    """

    def querying(*args, **kwargs):
        return f(get(), *args, **kwargs)

    return querying


# State versions of functions defined in the dicttools module.
# Each of these are identical to their corresponding dicttools function except for the
# omission of the first argument d.
getitem = _querying_fn(dt.getitem)
setitem = _mutating_fn(dt.setitem)
update = _mutating_fn(dt.update)
delete = _mutating_fn(dt.delete)
remove = _mutating_fn(dt.remove)
append = _mutating_fn(dt.append)
contains = _querying_fn(dt.contains)
exists = _querying_fn(dt.exists)


def register_listener(on_update, on_ready=None):
    """
    The basic mechanism for listening to state changes. Adds an update event and returns 2
    functions.

    - listen(): Starts a blocking loop listening for update events, calling on_update(old, new)
                whenever that happens.
    - stop_listening(): Stops the loop when called from another thread or process.
    """
    did_update_event = _mgr.Event()
    stop_event = mp.Event()

    _did_update_events.append(did_update_event)
    old = get()

    def listen():
        nonlocal old
        try:
            if on_ready is not None:
                on_ready()

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


class StateDispatcher:
    """
    Listens for state updates and run callbacks when specific state paths have changed value.

    - listen() - Start the listening loop (usually done from a new thread or process).
    - stop() - Stop the listening loop.
    """

    def __init__(self):
        super().__init__()
        self._dispatch_table = dict()
        self._ready_event = mp.Event()

        def on_update(old, new):
            for path, on_update in self._dispatch_table.items():
                old_val = dt.getitem(old, path, None)
                new_val = dt.getitem(new, path, None)

                if not old_val == new_val:
                    on_update(old_val, new_val)

        def on_ready():
            self._ready_event.set()

        self.listen, self.stop = register_listener(on_update, on_ready)

    def wait_until_ready(self, timeout=None):
        """Return once the dispatcher thread is ready, or <timeout> seconds passed (unless timeout is None)"""
        return self._ready_event.wait(timeout)

    def add_callback(self, path, on_update):
        """
        Add a callback to the dispatch table. Aftwards, whenever a state update changes the value
        at path, the on_update(old_val, new_val) function will be called.

        If a callback was previously set with this path, it will be overwritten.
        """
        self._dispatch_table[path] = on_update

    def remove_callback(self, path):
        """
        Remove and return the callback set to this state path.
        """
        return self._dispatch_table.pop(path)


def partial_path_fn(f, path_prefix):
    """
    Return a function the calls path function f with the supplied path_prefix concatenated to the
    beginning of its 1st arg.
    """

    def fn(path, *args, **kwargs):
        if isinstance(path, str):
            path = (path,)

        return f(path_prefix + path, *args, **kwargs)

    return fn


class CursorException(Exception):
    pass


class Cursor:
    """
    a Cursor points to a specific state path and provides a shorthand way to mutate or query
    this path and its children. The class implements partial path versions of each state function,
    which accept a partial state path starting from the Cursor's root key. For example:

    c = state.get_cursor(("x", "y"))
    c.update("z", {"a": 0, "b": 1})

    This will update the dictionary at state path ("x", "y", "z") with the new supplied values.
    see the dicttools module docs for the full list of available functions/methods.

    Cursors are usually created by calling the get_cursor() method of another higher-level Cursor.
    The global state attribute (see below) holds a Cursor pointing to the root state path.

    Subscript operators:
    cursor[x] will return a copy of the value at state path x.
    cursor[x] = y will update the state with the new value y at state path x.

    in operator:
    `key in cursor` will return true if the state at the cursor path contains key.
    `path in cursor` when used with a tuple, return true if the path exists as a sub path of this cursor.

    Registering state update callbacks:
    When given a state_dispatcher on init, add_callback and remove_callback can be used to listen to
    state changes in sub-paths of the cursor (see StateDispatcher).
    """

    def __init__(self, path, state_dispatcher=None):
        if isinstance(path, str):
            path = (path,)

        self.state_dispatcher = state_dispatcher
        self.path = path
        self.get = partial_path_fn(getitem, path)
        self.get.__doc__ = (
            """get(path, default=dicttools.path_not_found) - See dicttools.getitem"""
        )

        self.setitem = partial_path_fn(setitem, path)
        self.setitem.__doc__ = """setitem(path, v)"""

        self.update = partial_path_fn(update, path)
        self.update.__doc__ = """update(path, kvs)"""

        self.delete = partial_path_fn(delete, path)
        self.delete.__doc__ = """delete(path)"""

        self.remove = partial_path_fn(remove, path)
        self.remove.__doc__ = """remove(path, v)"""

        self.append = partial_path_fn(append, path)
        self.append.__doc__ = """append(path, v)"""

        self.contains = partial_path_fn(contains, path)
        self.contains.__doc__ = """contains(path, v)"""

        self.exists = partial_path_fn(exists, path)
        self.exists.__doc__ = """exists(path)"""

    def get_self(self, *args, **kwargs):
        """
        Return a deep copy of the current state starting from the cursor path.
        Accepts a default arg (see dicttols.getitem)
        """
        if self.path == ():
            return get(*args, **kwargs)
        else:
            return getitem(self.path, *args, **kwargs)

    def set_self(self, value):
        """
        Updates the state with the cursor path set to value.
        """
        if self.path == ():
            return set(value)
        else:
            return setitem(self.path, value)

    def parent(self):
        """
        Return a cursor pointing to the parent path of this cursor.
        When called on the root state cursor raise a KeyError exception.
        """
        if len(self.path) == 0:
            raise KeyError(f"path {self.path} has no parent.")

        return Cursor(self.path[:-1])

    def absolute_path(self, rel_path):
        """
        Return an absolute state path by concatenating the cursor path with rel_path.
        """
        if isinstance(rel_path, str):
            rel_path = (rel_path,)

        return self.path + rel_path

    def get_cursor(self, path):
        """
        Return a new cursor pointing to the supplied sub path of this cursor.
        """
        return Cursor(self.absolute_path(path), self.state_dispatcher)

    def add_callback(self, path, on_update):
        """
        Add on_update as a callback for state updates at the supplied cursor sub path.
        """
        if self.state_dispatcher is None:
            raise CursorException(
                "This Cursor doesn't have a StateDispatcher assigned."
            )

        self.state_dispatcher.add_callback(self.absolute_path(path), on_update)

    def remove_callback(self, path):
        """
        Remove and return the state update callback at the supplied cursor sub path.
        """
        if self.state_dispatcher is None:
            raise CursorException(
                "This Cursor doesn't have a StateDispatcher assigned."
            )

        return self.state_dispatcher.remove_callback(self.absolute_path(path))

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


# A cursor pointing to the state root.
state = Cursor(())
