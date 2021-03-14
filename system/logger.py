import state
import threading
import sys
import logging.handlers
import traceback

_formatter = logging.Formatter(
    "%(asctime)s %(processName)-10s %(levelname)-8s %(message)s",
    datefmt="%Y-%d-%m %H:%M:%S",
)


def listener_configurer(handler):
    print(handler)
    log = logging.getLogger("mp_log_listener")
    # h = logging.handlers.RotatingFileHandler("mptest.log", "a", 300, 10)
    handler.setFormatter(_formatter)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(_formatter)
    log.addHandler(handler)
    log.addHandler(stderr_handler)
    return log


# This is the listener process top-level loop: wait for logging events
# (LogRecords)on the queue and handle them, quit when you get a None for a
# LogRecord.
def listener_thread(queue):
    while True:
        try:
            record = queue.get()
            if (
                record is None
            ):  # We send this as a sentinel to tell the listener to quit.
                break
            logger = logging.getLogger("mp_log_listener")
            logger.handle(record)  # No level or filter logic applied - just do it!
        except Exception:
            print("Whoops! Problem:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


def logger_configurer(name=None):
    h = logging.handlers.QueueHandler(_log_queue)  # Just the one handler needed
    if name is None:
        root = logging.getLogger()
    else:
        root = logging.getLogger(name)
    root.addHandler(h)
    root.setLevel(logging.DEBUG)


_log_queue = None
_log_listener = None
_listener_configurer = None


def init(output_handler):
    global _log_queue, _log_listener, _listener_configurer
    _log_queue = state._mgr.Queue(-1)
    listener_configurer(output_handler)
    _log_listener = threading.Thread(target=listener_thread, args=(_log_queue,))
    _log_listener.start()


def shutdown():
    if _log_queue is not None:
        _log_queue.put_nowait(None)
    if _log_listener is not None:
        _log_listener.join()
