import config
import state
import threading
import sys
import logging.handlers
import traceback

formatter = logging.Formatter(
    "%(asctime)s %(name)s %(levelname)-8s %(message)s",
    datefmt="%Y-%d-%m %H:%M:%S",
)


def listener_configurer(handlers):
    """
    Configure the listener log. Add the supplied handlers.
    """
    log = logging.getLogger("mp_log_listener")
    for handler in handlers:
        log.addHandler(handler)

    return log


def listener_thread(queue):
    """
    Thread function that listens for incoming log records on the supplied queue.
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


def logger_configurer(name=None, level=config.log_level):
    """
    Configures the root logger of the current process to send messages to the log queue.
    This is typically called in the run() method or target function of a process.
    """
    h = logging.handlers.QueueHandler(_log_queue)  # Just the one handler needed
    if name is None:
        root = logging.getLogger()
    else:
        root = logging.getLogger(name)
    root.addHandler(h)
    root.setLevel(level)
    return root


def patch_threading_excepthook():
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


def excepthook(exc_type, exc_value, exc_traceback, thread_name=None):
    """
    Sends exception messages to the main logger. A sys.excepthook function.
    """
    if thread_name is None:
        msg = "Exception on main thread:"
    else:
        msg = f"Exception at thread {thread_name}:"
    main_logger.critical(msg, exc_info=(exc_type, exc_value, exc_traceback))


_log_queue = None
_log_listener = None
_listener_configurer = None
main_logger = None


def init(log_handlers):
    global _log_queue, _log_listener, _listener_configurer, main_logger

    main_logger = logging.getLogger("Main")
    for handler in log_handlers:
        main_logger.addHandler(handler)

    main_logger.setLevel(logging.INFO)

    sys.excepthook = excepthook
    patch_threading_excepthook()

    _log_queue = state._mgr.Queue(-1)
    listener_configurer(log_handlers)
    _log_listener = threading.Thread(target=listener_thread, args=(_log_queue,))
    _log_listener.start()

    return main_logger


def shutdown():
    if _log_queue is not None:
        _log_queue.put_nowait(None)
    if _log_listener is not None:
        _log_listener.join()
