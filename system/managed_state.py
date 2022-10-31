"""
Multi-process, shared, state store implementation based on multiprocessing.Manager
Author: Tal Eisenberg, 2021

The state store maintains a shared dictionary. Access to the dictionary is synchronized between processes and threads
by creating a deep copy of the full dictionary on each read, and replacing the full dictionary when updating any of its
values (i.e. the dictionary is immutable). This makes dictionary access quite slow compared to a local dict, however
the difference in performance should be negligble for small dictionaries (up to a few thousand elements).

Since the whole dictionary is copied on every read, and changing any value requires replacing the whole
dictionary, reading and writing state values should be done using Cursor objects.

In addition to sharing data between processes and threads, the state store can be used for synchronization
by changing a value from one process and listening for changes of this value from another process. This is possible
by using the StateDispatcher class.

Module classes:
- StateStore: Provides an arbitrarly nested dictionary that can be safely accessed by multiple threads
              and processes by using a multiprocessing.managers.SyncManager.
- Cursor: Reading and writing the state store dictionary is done using the Cursor class.
- StateDispatcher: Makes it possible to register callback functions that will run whenever specific state
                   values are updated.
"""
from copy import deepcopy
import multiprocessing as mp
from multiprocessing.managers import DictProxy, SyncManager
import signal
import dicttools as dt


class _StateManager(SyncManager):
    pass


class CursorException(Exception):
    pass


class Cursor:
    """
    A cursor pointing to a specific path within the state store dictionary.
    The path is a sequence of keys and/or indices leading to a specific value under the nested state dictionary.
    It can be either a string key, an int index (for sub-lists), or a tuple of keys and indices. For example, the
    path ("x", "y", "z") corresponds to the "z" key of the dict under the "y" key of the dict under the "x" key of
    the state.

    The Cursor maintains a connection to a state store server and allows reading and writing state values under
    the specified cursor path. It provides a number of methods to access the state values as well as indexing
    operations. When a Cursor method accepts a path argument it is a __relative path__ in respect to the base path
    of the Cursor.

    Example usage:
    ```
    x = Cursor(("a", "b", 0))
    y = x["c"]
    z = x["c", "d"]
    ```

    Additional supported operators:
    - `cursor[path]` is equivalent to cursor.get(path)
    - `cursor[path] = x` will set the value at `path` to `x`.
    - `path in cursor` will evaluate to True if the relative state path exists.

    In the preceding code y would be assigned the value at state["a"]["b"][0]["c"], and z would be assigned
    the value at state["a"]["b"][0]["c"]["d"].

    A Cursor can create a new SyncManager for connecting to the state store server, but it can also share
    an existing manager that was created by another cursor as long as they both run on the same process.

    The Cursor can also be used to get, add or remove shared multiprocessing.Event objects. This provides a
    way to synchronize multiple processes with a very low overhead.
    """
    def __init__(
        self,
        path,
        authkey=None,
        address=None,
        manager=None,
        state_dispatcher=None,
    ) -> None:
        """
        Initialize a Cursor.

        Args:
        - path: tuple, string, or int. The base path the cursor points to (see class docstring for more information).
        - authkey: string. An authkey for connecting to the SyncManager
        - address: tuple (host, port). The host and port of the Manager server.
        - manager: An optional SyncManager. This can be used to share managers between cursors on the same process.
        - state_dispatcher: An optional StateDispatcher object. Should not be used normally. StateDispatcher receive a
                            Cursor on initialization and will set that Cursor's state_dispatcher property on initialization.
        """
        self._mgr = manager
        self._address = address
        self._state_dispatcher = state_dispatcher
        self._authkey = authkey

        if isinstance(path, str):
            self.path = (path,)
        else:
            self.path = path

        if self._mgr is None:
            _StateManager.register("get")
            self._mgr = _StateManager(
                address=self._address, authkey=self._authkey.encode("ASCII")
            )
            self._mgr.connect()
            mp.current_process().authkey = authkey.encode("ASCII")
            self._store = self._mgr.get()
            if "lock" not in self._store:
                self._store["lock"] = self._mgr.Lock()
            if "state" not in self._store:
                self._store["state"] = self._mgr.dict()
            if "did_update_events" not in self._store:
                self._store["did_update_events"] = self._mgr.list()
            if "events" not in self._store:
                self._store["events"] = self._mgr.dict()
            if "event_change_events" not in self._store:
                self._store["event_change_events"] = self._mgr.dict()
        else:
            self._store = self._mgr.get()

    def _notify(self):
        for e in self._store["did_update_events"]:
            e.set()

    def _get_lock(self):
        return self._store["lock"]

    def _get_state(self):
        return deepcopy(self._store["state"])

    def _set_state(self, new_state):
        self._store["state"] = self._mgr.dict(new_state)

    def _setitem(self, path, v):
        with self._get_lock():
            self._set_state(dt.setitem(self._get_state(), path, v))

        self._notify()

    def get(self, path, default=dt.path_not_found):
        """
        Return the state value at a specific path or the default value if the path does not exist.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor.
        - default: A default value in case the path does not exist. Using dicttools.path_not_found will result
                   in raising a KeyError exception if the path does not exist.
        """
        return dt.getitem(self._get_state(), self.absolute_path(path), default)

    def get_self(self, default=dt.path_not_found):
        """
        Return the state value at the Cursor path.

        Args:
        - default: A default value in case the path does not exist. Using dicttools.path_not_found will result
            in raising a KeyError exception if the path does not exist.
        """
        return self.get((), default=default)

    def set_self(self, v):
        """
        Set the value at the Cursor path to `v`.
        """
        if self.path == ():
            with self._get_lock():
                self._set_state(v)

            self._notify()
        else:
            self._setitem(self.absolute_path(()), v)

    def update(self, path, kvs):
        """
        Update a dictionary at a specific state path by adding the contents of the supplied dict.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor. The value
                at this path must be a dict.
        - kvs: A dict. Keys and values from this dict will be added to the state dict.
        """
        with self._get_lock():
            self._set_state(dt.update(self._get_state(), self.absolute_path(path), kvs))

        self._notify()

    def delete(self, path):
        """
        Delete the value at a specific state path.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor. The value
                at this path must belong to a collection with a pop() function (e.g. list or dict).
        """
        with self._get_lock():
            self._set_state(dt.delete(self._get_state(), self.absolute_path(path)))

        self._notify()

    def remove(self, path, v):
        """
        Remove element `v` from a list at a specific state path.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor. The value
                at this path must be a list.
        - v: The value that will be removed.
        """
        with self._get_lock():
            self._set_state(dt.remove(self._get_state(), self.absolute_path(path), v))

        self._notify()

    def append(self, path, v):
        """
        Append an element `v` to a list at a specific state path.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor. The value
                at this path must be a list.
        - v: The value that will be appended.
        """
        with self._get_lock():
            self._set_state(dt.append(self._get_state(), self.absolute_path(path), v))

        self._notify()

    def contains(self, path, v):
        """
        Return True if the value at a specific state path contains the value `v`.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor.
        - v: The value that will be appended.

        """
        return dt.contains(self._get_state(), self.absolute_path(path), v)

    def exists(self, path):
        """
        Return True if a specific path exists.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor.
        """
        return dt.exists(self._get_state(), self.absolute_path(path))

    def __getitem__(self, path):
        return self.get(path)

    def __setitem__(self, path, v):
        self._setitem(self.absolute_path(path), v)

    def __contains__(self, k):
        if type(k) is tuple:
            if len(k) > 1:
                return self.exists(k)
            else:
                k = k[0]

        return self.contains((), k)

    def __str__(self) -> str:
        return f"Cursor({self.path})"

    def absolute_path(self, rel_path):
        """
        Return an absolute state path by concatenating the cursor path with rel_path.

        Args:
        - rel_path: tuple, string or int. A path relative to the base path of the Cursor.
        """
        if isinstance(rel_path, str):
            rel_path = (rel_path,)

        return self.path + rel_path

    def parent(self):
        """
        Return a cursor pointing to the parent path of this cursor. The new cursor can only be used
        in the same process as this cursor.

        When called on the root state cursor a KeyError exception is raised.
        """
        if len(self.path) == 0:
            raise KeyError(f"path {self.path} has no parent.")

        return self.get_cursor(self.path[:-1], absolute_path=True)

    def root(self):
        return self.get_cursor((), absolute_path=True)

    def get_cursor(self, path, absolute_path=False):
        """
        Return a new cursor pointing to a new state path. The new cursor can only be used
        in the same process as this cursor since they share a SyncManager.

        Args:
            - path: tuple, string or int. A relative or absolute path the new cursor will point to.
            - absolute_path: When True the path argument will be considered an absolute state path otherwise
                             the new cursor path will be relative to this Cursor path.
        """

        return Cursor(
            path if absolute_path else self.absolute_path(path),
            manager=self._mgr,
            state_dispatcher=self._state_dispatcher,
            address=self._address,
            authkey=self._authkey,
        )

    def register_listener(self, on_update, on_ready=None):
        """
        The basic mechanism for listening to state changes. Adds an update event and returns 2
        functions. a StateDispatcher should be used instead of this for listening to changes in specific
        state paths.        

        - listen(): Starts a blocking loop listening for update events, calling on_update(old, new)
                    whenever that happens.
        - stop_listening(): Stops the loop when called from another thread or process.
        """
        did_update_event = self._mgr.Event()
        stop_event = mp.Event()

        self._store["did_update_events"].append(did_update_event)
        old = self._get_state()

        def listen():
            nonlocal old
            try:
                if on_ready is not None:
                    on_ready()

                while True:
                    try:
                        did_update_event.wait()
                    except ConnectionError:
                        break

                    if stop_event.is_set():
                        break
                    did_update_event.clear()
                    new = self._get_state()
                    on_update(old, new)
                    old = new
            except EOFError:
                pass

        def stop_listening():
            stop_event.set()
            try:
                did_update_event.set()
            except ConnectionResetError:
                pass

        return listen, stop_listening

    def add_callback(self, path, on_update):
        """
        Add on_update as a callback for state updates at the supplied cursor sub path.
        The Cursor must have a StateDispatcher assigned.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor.
        - on_update: a function f(old, new) where `old` is the previous value of this state path, and `new` 
                     is the new value. This function will be called whenever the value at the state path changes.
        """
        if self._state_dispatcher is None:
            raise CursorException(
                "This Cursor doesn't have a StateDispatcher assigned."
            )

        self._state_dispatcher.add_callback(self.absolute_path(path), on_update)

    def remove_callback(self, path):
        """
        Remove and return the state update callback for the supplied cursor sub path.

        Args:
        - path: tuple, string or int. A path relative to the base path of the Cursor.
        """
        if self._state_dispatcher is None:
            raise CursorException(
                "This Cursor doesn't have a StateDispatcher assigned."
            )

        return self._state_dispatcher.remove_callback(self.absolute_path(path))

    def get_event(self, owner, name):
        """
        Return an event from the event store corresponding to the supplied owner and name.
        """
        if owner not in self._store["events"]:
            self._store["events"][owner] = {}

        if name not in self._store["events"][owner]:
            e = self._mgr.Event()
            with self._get_lock():
                owner_store = self._store["events"][owner]
                owner_store[name] = e
                self._store["events"][owner] = owner_store
            self._notify_events_changed(owner)
            return e
        else:
            return self._store["events"][owner][name]

    def _notify_events_changed(self, owner):
        if owner in self._store["event_change_events"]:
            event = self._store["event_change_events"][owner]
            if event:
                event.set()

    def remove_event(self, owner, name):
        """
        Remove an event from the event store corresponding to the supplied owner and name.
        """
        if owner in self._store["events"] and name in self._store["events"][owner]:
            with self._get_lock():
                owner_store = self._store["events"][owner]
                del owner_store[name]
                self._store["events"][owner] = owner_store

            self._notify_events_changed(owner)
        else:
            raise KeyError(f"Event {owner}.{name} doesn't exist")

    def add_events_changed_event(self, owner):
        """
        Return a multiprocessing.Event object that will be set whenever the event list for a specific owner changes.

        - owner: string. The owner whose event list should be observed
        """
        event = self._mgr.Event()
        self._store["event_change_events"][owner] = event
        return event

    def get_events(self, owner):
        """
        Return all events that are registered for a specific owner, or an empty dict if there are none.

        - owner: string. The owner of the event list.
        """
        if owner not in self._store["events"]:
            return {}
        else:
            return self._store["events"][owner]


class StateStore:
    """
    Maintain a SyncManager server on a child process.
    """
    def __init__(self, address, authkey) -> None:
        """
        Start a new process, create a SyncManager server, and start listening for connections.

        Args:
        - address: tuple (host: str, port: int). The server will listen for connnections on this address.
        - authkey: str. The authentication key for checking the validity of incoming connections.
        """
        self.authkey = authkey
        self.address = address
        self.managerProcess = mp.Process(target=self._start_manager, daemon=True)
        self.managerProcess.start()

    def _start_manager(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        store = {}
        _StateManager.register("get", lambda: store, DictProxy)
        mgr = _StateManager(address=self.address, authkey=self.authkey.encode("ASCII"))
        mgr.get_server().serve_forever()

    def shutdown(self):
        """
        Terminate the store SyncManager process.
        """
        self.managerProcess.terminate()


class StateDispatcher:
    """
    Listens for state updates and run callbacks when specific state paths have changed value.

    - listen() - Start the listening loop (usually done from a new thread or process).
    - stop() - Stop the listening loop.
    """

    def __init__(self, state: Cursor):
        """
        Initialize a StateDispatcher that will be tied to the supplied state Cursor.

        Args:
        - state: a Cursor pointing to some path of some state store.
        """
        super().__init__()
        state._state_dispatcher = self
        self._dispatch_table = dict()
        self._ready_event = mp.Event()

        def on_update(old, new):
            try:
                for path, on_update in self._dispatch_table.items():
                    old_val = dt.getitem(old, path, None)
                    new_val = dt.getitem(new, path, None)

                    if not old_val == new_val:
                        on_update(old_val, new_val)
            except RuntimeError:
                pass

        def on_ready():
            self._ready_event.set()

        self.listen, self.stop = state.register_listener(on_update, on_ready)

    def wait_until_ready(self, timeout=None):
        """
        Return once the dispatcher thread is ready, or <timeout> seconds passed (unless timeout is None)
        """
        return self._ready_event.wait(timeout)

    def add_callback(self, path, on_update):
        """
        Add a callback to the dispatch table. Aftwards, whenever a state update changes the value
        at `path`, the `on_update(old_val, new_val)` function will be called.

        If a callback was previously set with this path, it will be replaced.
        """
        self._dispatch_table[path] = on_update

    def remove_callback(self, path):
        """
        Remove and return the callback set to this state `path`.
        """
        return self._dispatch_table.pop(path)
