from copy import deepcopy
import multiprocessing as mp
from multiprocessing.managers import DictProxy, SyncManager
import dicttools as dt
import threading
from time import sleep
import dicttools

# TODO: docstrings


class _StateManager(SyncManager):
    pass


class CursorException(Exception):
    pass


class Cursor:
    def __init__(
        self, path, manager=None, state_dispatcher=None, authkey=b"reptilearn-state"
    ) -> None:
        self._mgr = manager
        self._state_dispatcher = state_dispatcher

        if isinstance(path, str):
            self.path = (path,)
        else:
            self.path = path

        if self._mgr is None:
            _StateManager.register("get")
            self._mgr = _StateManager(address=("127.0.0.1", 50000), authkey=authkey)
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

    def _get_lock(self):
        return self._managed_data["lock"]

    def _get_state(self):
        return deepcopy(self._managed_data["state"])

    def _set_state(self, new_state):
        self._managed_data["state"] = self._mgr.dict(new_state)

    def _setitem(self, path, v):

        with self._get_lock():
            new_state = dicttools.setitem(self._get_state(), path, v)
            self._set_state(new_state)

        for e in self._managed_data["did_update_events"]:
            e.set()

    def get(self, path, default=dicttools.path_not_found):
        """
        get(path, default=dicttools.path_not_found) - See dicttools.getitem
        """
        return dicttools.getitem(self._get_state(), self.absolute_path(path), default)

    def get_self(self, default=dicttools.path_not_found):
        return self.get((), default=default)

    def set_self(self, v):
        if self.path == ():
            self._set_state(v)
        else:
            self._setitem(self.absolute_path(()), v)

    def update(self, path, kvs):
        self._set_state(
            dicttools.update(self._get_state(), self.absolute_path(path), kvs)
        )

    def delete(self, path):
        self._set_state(dicttools.delete(self._get_state(), self.absolute_path(path)))

    def remove(self, path, v):
        self._set_state(
            dicttools.remove(self._get_state(), self.absolute_path(path), v)
        )

    def append(self, path, v):
        self._set_state(
            dicttools.append(self._get_state(), self.absolute_path(path), v)
        )

    def contains(self, path, v):
        return dicttools.contains(self._get_state(), self.absolute_path(path), v)

    def exists(self, path):
        return dicttools.exists(self._get_state(), self.absolute_path(path))

    def __getitem__(self, path):
        return self.get(path)

    def __setitem__(self, path, v):
        self._setitem(self.absolute_path(path), v)

    def __contains__(self, k):
        if type(k) is tuple:
            if len(k) > 1:
                return self.exists(self.path + k)
            else:
                k = k[0]

        return self.contains(self.path, k)

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
            self.path[:-1], manager=self._mgr, state_dispatcher=state_dispatcher
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
                    did_update_event.wait()
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
            did_update_event.set()

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
    def __init__(self, authkey=b"reptilearn-state") -> None:
        self.authkey = authkey
        mp.Process(target=self.managerProcess, daemon=True).start()

    def managerProcess(self):
        managed_data = {}
        _StateManager.register("get", lambda: managed_data, DictProxy)

        try:
            mgr = _StateManager(address=("127.0.0.1", 50000), authkey=self.authkey)
            mgr.get_server().serve_forever()
        except OSError:
            # failed to listen on port - already in use.
            pass


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
            for path, on_update in self._dispatch_table.items():
                old_val = dt.getitem(old, path, None)
                new_val = dt.getitem(new, path, None)

                if not old_val == new_val:
                    on_update(old_val, new_val)

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


# ########## TEST FROM HERE (REMOVE EVENTUALLY)
class ProcessWithState(mp.Process):
    def __init__(self) -> None:
        super().__init__()

    def run(self):
        print(f"Process {mp.current_process().name} starting")
        self.video_state = Cursor("video")

        if not self.video_state.exists(()):
            self.video_state.set_self({})

        self.video_state[self.name] = 0

        while True:
            self.video_state[self.name] = self.video_state[self.name] + 1
            sleep(1)


if __name__ == "__main__":
    state = StateStore()

    root = None
    # try until the state server is working
    while root is None:
        try:
            print("try")
            root = Cursor(())
        except Exception:
            sleep(0.01)

    root["main"] = "hi"
    dispatcher = StateDispatcher(root)
    threading.Thread(target=dispatcher.listen).start()

    def callback_fn(old, new):
        print("old:", old, "\n", "new:", new, "\n")

    root.add_callback("video", callback_fn)
    ps = [ProcessWithState() for _ in range(4)]
    for p in ps:
        p.start()

    while True:
        root["main"] = root["main"] + " hi"
        print(root[()])
        sleep(1)
