"""
Provide facilities for multiprocess logging, logging exception, logging handlers for session log files
and socketio logging.
Author: Tal Eisenberg, 2021

Starts a listening thread that receives log records from other processes, and outputs them through the
main process. Processes should call logger_configurer() from the process run method or target function to
setup the process root logger to send log records to the listener.
"""

from collections import deque
import multiprocessing as mp
import threading
import sys
import logging.handlers
import traceback
from state import state

_default_level = None
_log_queue = None
_log_listener = None
_log_buffer = None

# The default log formatter
formatter = logging.Formatter(
    "%(asctime)s %(name)s %(levelname)-8s %(message)s",
    datefmt="%Y-%d-%m %H:%M:%S",
)


class SocketIOHandler(logging.Handler):
    """
    a Log handler that emits log records over socketio events.
    The handler uses rl_logging.formatter by default.
    """
    def __init__(self, socketio, event_name="log"):
        """
        - socketio: The socketio object created by the flask-socketio library.
        - event_name: The name of the event log records will be sent to.
        """
        super().__init__()
        self.socketio = socketio
        self.event_name = event_name
        self.setFormatter(formatter)

    def emit(self, record):
        self.socketio.emit(self.event_name, self.format(record))


class SessionLogHandler(logging.StreamHandler):
    """
    a Log handler that sends log records to session log files.
    The handler will create a log file in the session data directory once
    a session is created and start writing log records into it. Once the
    session is closed the handler will stop logging until a new one
    begins.

    The handler uses rl_logging.formatter by default.
    """
    def __init__(self, log_filename="session.log"):
        """
        - log_filename: The handler will create log files using this name in
                        new experiment data directories.
        """
        super().__init__()
        state.add_callback(("session", "data_dir"), self._on_dir_update)
        self.stream = None
        self.log_filename = log_filename
        self.setFormatter(formatter)

    def _on_dir_update(self, old, new):
        if self.stream is not None:
            self.acquire()
            self.stream.close()
            self.stream = None
            self.release()

        if new is not None:
            filename = new / self.log_filename
            self.stream = open(filename, "a")

    def emit(self, record):
        if self.stream is not None:
            logging.StreamHandler.emit(self, record)

    def close(self):
        self.acquire()
        try:
            try:
                if self.stream is not None:
                    try:
                        self.flush()
                    finally:
                        self.stream.close()
            finally:
                logging.StreamHandler.close(self)
        finally:
            self.release()


class LogBuffer(logging.Handler):
    """
    a Log handler that stores log records in a ring buffer.
    The handler uses rl_logging.formatter by default.
    """
    def __init__(self, buffer_size):
        """
        - buffer_size: Number of log lines that the buffer can hold.
        """
        super().__init__()
        self.d = deque(maxlen=buffer_size)
        self.setFormatter(formatter)

    def emit(self, record):
        self.d.append(self.format(record))

    def get_logs(self):
        """
        Return a list of all logs line that are stored in the buffer.
        """
        return list(self.d)

    def clear(self):
        """
        Clear the log buffer contents.
        """
        self.d.clear()


def logger_configurer(name=None, level=None):
    """
    Configures the root logger of the current process to send messages to the log queue.
    This is typically called in the run() method or target function of a process, and is
    required for routing log messages from child processes to the main process log handlers.
    """
    if level is None:
        level = _default_level

    h = logging.handlers.QueueHandler(_log_queue)  # Just the one handler needed
    if name is None:
        root = logging.getLogger()
    else:
        root = logging.getLogger(name)
    root.addHandler(h)
    root.setLevel(level)
    return root


def _listener_configurer(handlers):
    """
    Configure the listener log. Add the supplied handlers.
    """
    log = logging.getLogger("mp_log_listener")
    for handler in handlers:
        log.addHandler(handler)

    return log


def _listener_thread(queue):
    """
    a Thread function that listens for incoming log records on the supplied queue.
    Messages are logged to the "mp_log_listener" logger.

    The thread terminates when None is placed on the queue.
    """
    while True:
        try:
            try:
                record = queue.get()
            except BrokenPipeError:
                break
            except EOFError:
                break
            if (
                record is None
            ):  # We send this as a sentinel to tell the listener to quit.
                break
            logger = logging.getLogger("mp_log_listener")
            logger.handle(record)  # No level or filter logic applied - just do it!
        except Exception as e:
            print(f"Exception while listening for logs: {type(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


def _patch_threading_excepthook():
    """
    A hack for sending thread exceptions to our custom exception hook.

    Installs our exception handler into the threading modules Thread object
    Inspired by https://bugs.python.org/issue1230540
    """
    old_init = threading.Thread.__init__

    def new_init(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        old_run = self.run

        def run_with_our_excepthook(*args, **kwargs):
            try:
                old_run(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(
                    *sys.exc_info(), thread_name=threading.current_thread().name
                )

        self.run = run_with_our_excepthook

    threading.Thread.__init__ = new_init


def _excepthook(exc_type, exc_value, exc_traceback, thread_name=None):
    """
    Custom exception hook. Sends exception messages to the main logger.
    """
    if thread_name is None:
        msg = "Exception on main thread:"
    else:
        msg = f"Exception at thread {thread_name}:"
    logging.getLogger("Main").critical(msg, exc_info=(exc_type, exc_value, exc_traceback))


def get_log_buffer():
    if _log_buffer:
        return _log_buffer.get_logs()
    else:
        return None


def clear_log_buffer():
    if _log_buffer:
        _log_buffer.clear()

def init(log_handlers, log_buffer, extra_loggers, extra_log_level, default_level):
    """
    Initializes the main logger that is used for exceptions, and the multiprocess
    listening logger.

    - log_handlers: A sequence of log handlers that are attached to both loggers.
    - extra_loggers: Additional loggers that log_handlers should be added to.
    - extra_log_level: Log level of extra_loggers.
    - default_level: This will be the log level of each logger, including loggers on other processes.
    """
    global _log_queue, _log_listener, _default_level, _log_buffer

    _default_level = default_level
    _log_buffer = log_buffer
    log_handlers = list(log_handlers) + [log_buffer]

    main_logger = logging.getLogger("Main")
    for handler in log_handlers:
        main_logger.addHandler(handler)

    main_logger.setLevel(default_level)

    sys.excepthook = _excepthook
    _patch_threading_excepthook()

    _log_queue = mp.Queue(-1)
    _listener_configurer(log_handlers)
    _log_listener = threading.Thread(target=_listener_thread, args=(_log_queue,))
    _log_listener.start()

    for el in extra_loggers:
        for handler in log_handlers:
            el.addHandler(handler)
        el.setLevel(extra_log_level)

    return main_logger


def shutdown():
    """Shutdown the log listening queue and thread"""
    if _log_queue is not None:
        _log_queue.put_nowait(None)
    if _log_listener is not None:
        _log_listener.join()
