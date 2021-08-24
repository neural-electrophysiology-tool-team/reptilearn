from dynamic_loading import load_modules
import inspect
from schedule import on_datetime

_log = None
_config = None
_tasks = {}
_task_modules = []
_task_names = {}


def init(logger, config):
    global _log, _config
    _log = logger
    _config = config
    all_tasks()


def all_tasks():
    global _tasks, _task_modules, _task_names

    _tasks = {}
    _task_modules = load_modules(_config.tasks_modules_dir, _log)
    _task_names = {}

    for k, (m, s) in _task_modules.items():
        _tasks[k] = module_tasks(m)
        _task_names[k] = list(_tasks[k].keys())

    return _task_names


def module_tasks(module):
    public_fns = dict(
        (
            (name, func)
            for name, func in inspect.getmembers(module)
            if not name.startswith("_") and callable(func) and type(func) is not type
        )
    )
    return public_fns


def run(module, task):
    if module not in _tasks:
        raise Exception(f"Unknown task module: {module}")

    if task not in _tasks[module]:
        raise Exception(f"Unknown task {task} in module {module}.")

    fn = _tasks[module][task]
    sig = inspect.signature(fn)

    if len(sig.parameters) > 0:
        fn(_log)
    else:
        fn()


def schedule(module, task, dt):
    if module not in _tasks:
        raise Exception(f"Unknown task module: {module}")

    if task not in _tasks[module]:
        raise Exception(f"Unknown task {task} in module {module}.")

    cancel = on_datetime(lambda: run(module, task), dt)
