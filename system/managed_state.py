from copy import deepcopy
import multiprocessing as mp
from multiprocessing.managers import DictProxy, SyncManager
import signal
import dicttools as dt

# TODO: docstrings (stress that you can't do stuff like state[x][y] so you have to do state[x, y])


class _StateManager(SyncManager):
    pass


class CursorException(Exception):
    pass


class Cursor:
    def __init__(
        self,
        path,
        manager=None,
        state_dispatcher=None,
        authkey=b"reptilearn-state",
        address=("localhost", 50000),
    ) -> None:
        self._mgr = manager
        self._address = address
        self._state_dispatcher = state_dispatcher

        if isinstance(path, str):
            self.path = (path,)
        else:
            self.path = path

        if self._mgr is None:
            _StateManager.register("get")
            self._mgr = _StateManager(address=self._address, authkey=authkey)
            self._mgr.connect()
            mp.current_process().authkey = authkey
            self._managed_data = self._mgr.get()
            if "lock" not in self._managed_data:
                self._managed_data["lock"] = self._mgr.Lock()
            if "state" not in self._managed_data:
                self._managed_data["state"] = self._mgr.dict()
            if "did_update_events" not in self._managed_data:
                self._managed_data["did_update_events"] = self._mgr.list()
        else:
            self._managed_data = self._mgr.get()

    def _notify(self):
        for e in self._managed_data["did_update_events"]:
            e.set()

    def _get_lock(self):
        return self._managed_data["lock"]

    def _get_state(self):
        return deepcopy(self._managed_data["state"])

    def _set_state(self, new_state):
        self._managed_data["state"] = self._mgr.dict(new_state)

    def _setitem(self, path, v):

        with self._get_lock():
            self._set_state(dt.setitem(self._get_state(), path, v))

        self._notify()

    def get(self, path, default=dt.path_not_found):
        """
        get(path, default=dicttools.path_not_found) - See dicttools.getitem
        """
        return dt.getitem(self._get_state(), self.absolute_path(path), default)

    def get_self(self, default=dt.path_not_found):
        return self.get((), default=default)

    def set_self(self, v):
        if self.path == ():
            with self._get_lock():
                self._set_state(v)

            self._notify()
        else:
            self._setitem(self.absolute_path(()), v)

    def update(self, path, kvs):
        with self._get_lock():
            self._set_state(dt.update(self._get_state(), self.absolute_path(path), kvs))

        self._notify()

    def delete(self, path):
        with self._get_lock():
            self._set_state(dt.delete(self._get_state(), self.absolute_path(path)))

        self._notify()

    def remove(self, path, v):
        with self._get_lock():
            self._set_state(dt.remove(self._get_state(), self.absolute_path(path), v))

        self._notify()

    def append(self, path, v):
        with self._get_lock():
            self._set_state(dt.append(self._get_state(), self.absolute_path(path), v))

        self._notify()

    def contains(self, path, v):
        return dt.contains(self._get_state(), self.absolute_path(path), v)

    def exists(self, path):
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
        """
        if isinstance(rel_path, str):
            rel_path = (rel_path,)

        return self.path + rel_path

    def parent(self, state_dispatcher="inherit"):
        """
        Return a cursor pointing to the parent path of this cursor. The new cursor can only be used
        in the same process as this cursor.

        When called on the root state cursor a KeyError exception is raised.

        - state_dispatcher: This will become the state_dispatcher of the new Cursor. The default "inherit" value means to use the dispatcher of this cursor.
        """
        if len(self.path) == 0:
            raise KeyError(f"path {self.path} has no parent.")

        if state_dispatcher == "inherit":
            state_dispatcher = self._state_dispatcher

        return Cursor(
            self.path[:-1],
            manager=self._mgr,
            state_dispatcher=state_dispatcher,
            address=self._address,
        )

    def root(self, state_dispatcher="inherit"):
        if state_dispatcher == "inherit":
            state_dispatcher = self._state_dispatcher

        return Cursor(
            (),
            manager=self._mgr,
            state_dispatcher=state_dispatcher,
            address=self._address,
        )

    def get_cursor(self, path, state_dispatcher="inherit"):
        """
        Return a new cursor pointing to the supplied sub path of this cursor. The new cursor can only be used
        in the same process as this cursor.

        - state_dispatcher: This will become the state_dispatcher of the new Cursor. The default "inherit" value means to use the dispatcher of this cursor.
        """
        if state_dispatcher == "inherit":
            state_dispatcher = self._state_dispatcher

        return Cursor(
            self.absolute_path(path),
            manager=self._mgr,
            state_dispatcher=state_dispatcher,
            address=self._address,
        )

    def register_listener(self, on_update, on_ready=None):
        """
        The basic mechanism for listening to state changes. Adds an update event and returns 2
        functions.

        - listen(): Starts a blocking loop listening for update events, calling on_update(old, new)
                    whenever that happens.
        - stop_listening(): Stops the loop when called from another thread or process.
        """
        did_update_event = self._mgr.Event()
        stop_event = mp.Event()

        self._managed_data["did_update_events"].append(did_update_event)
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
        """
        if self._state_dispatcher is None:
            raise CursorException(
                "This Cursor doesn't have a StateDispatcher assigned."
            )

        self._state_dispatcher.add_callback(self.absolute_path(path), on_update)

    def remove_callback(self, path):
        """
        Remove and return the state update callback at the supplied cursor sub path.
        """
        if self._state_dispatcher is None:
            raise CursorException(
                "This Cursor doesn't have a StateDispatcher assigned."
            )

        return self._state_dispatcher.remove_callback(self.absolute_path(path))


class StateStore:
    def __init__(
        self, address=("localhost", 50000), authkey=b"reptilearn-state"
    ) -> None:
        self.authkey = authkey
        self.address = address
        self.managerProcess = mp.Process(target=self.start_manager, daemon=True)
        self.managerProcess.start()

    def start_manager(self):
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        managed_data = {}
        _StateManager.register("get", lambda: managed_data, DictProxy)
        mgr = _StateManager(address=self.address, authkey=self.authkey)
        mgr.get_server().serve_forever()

    def shutdown(self):
        self.managerProcess.terminate()


class StateDispatcher:
    """
    Listens for state updates and run callbacks when specific state paths have changed value.

    - listen() - Start the listening loop (usually done from a new thread or process).
    - stop() - Stop the listening loop.
    """

    def __init__(self, state: Cursor):
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
        """Return once the dispatcher thread is ready, or <timeout> seconds passed (unless timeout is None)"""
        return self._ready_event.wait(timeout)

    def add_callback(self, path, on_update):
        """
        Add a callback to the dispatch table. Aftwards, whenever a state update changes the value
        at path, the on_update(old_val, new_val) function will be called.

        If a callback was previously set with this path, it will be removed.
        """
        self._dispatch_table[path] = on_update

    def remove_callback(self, path):
        """
        Remove and return the callback set to this state path.
        """
        return self._dispatch_table.pop(path)
