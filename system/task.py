"""
Task scheduling of dynamically loaded task functions.

Author: Tal Eisenberg, 2021
"""
from dynamic_loading import load_modules
import inspect
from rl_logging import get_main_logger
import schedule as sched
from configure import get_config
from dateutil import parser
from datetime import datetime

_log = None
_tasks = {}
_task_modules = []
_task_names = {}
_task_pool = "__tasks__"
_scheduled_tasks = []
_last_scheduled_task_id = 0


def init():
    global _log
    _log = get_main_logger()

    all_tasks()


def all_tasks():
    global _tasks, _task_modules, _task_names

    _tasks = {}
    _task_modules = load_modules(get_config().tasks_modules_dir, _log)
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


def scheduled_tasks():
    return [
        {k: v for k, v in t.items() if k != "cancel_fn"}
        for t in _scheduled_tasks
        if sched.is_scheduled(t["cancel_fn"], pool=_task_pool)
    ]


def get_new_scheduled_task_id():
    global _last_scheduled_task_id
    _last_scheduled_task_id += 1
    return _last_scheduled_task_id


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


def schedule_task(module, task, task_type, **kwargs):
    if module not in _tasks:
        raise Exception(f"Unknown task module: {module}")

    if task not in _tasks[module]:
        raise Exception(f"Unknown task {task} in module {module}.")

    if task_type == "datetime":
        if type(kwargs["dt"]) is str:
            dt = parser.parse(kwargs["dt"]).astimezone()
        else:
            dt = kwargs["dt"]

        cancel = sched.on_datetime(lambda: run(module, task), dt, pool=_task_pool)
        _log.info(f"Scheduled task {module}.{task} at {dt}")

    elif task_type == "interval":
        cancel = sched.repeat(
            lambda: run(module, task),
            kwargs["interval"],
            kwargs["repeats"],
            pool=_task_pool,
        )
        _log.info(
            f"Scheduled task {module}.{task}. interval={kwargs['interval']} seconds, repeats={kwargs['repeats']}"
        )

    elif task_type == "timeofday":
        if type(kwargs["dt"]) is str:
            dt = parser.parse(kwargs["dt"]).astimezone()
        else:
            dt = kwargs["dt"]

        time = dt.time()

        cancel = sched.timeofday(
            lambda: run(module, task), time, kwargs["repeats"], pool=_task_pool
        )
        if kwargs["repeats"] is True:
            _log.info(f"Scheduled task {module}.{task} at {dt}. Repeats every day")
        else:
            _log.info(
                f"Scheduled task {module}.{task} at {time}. Repeats for {kwargs['repeats']} day(s)"
            )

    else:
        raise ValueError(f"Unknown task type: {task_type}")

    _scheduled_tasks.append(
        {
            "task": f"{module}.{task}",
            "task_type": task_type,
            "params": kwargs,
            "created": datetime.now(),
            "cancel_fn": cancel,
            "task_id": get_new_scheduled_task_id(),
        }
    )


def cancel_task(task_id):
    tasks = [t for t in _scheduled_tasks if t["task_id"] == task_id]
    if len(tasks) == 0:
        raise ValueError(f"Unknown task_id: {task_id}")
    task = tasks[0]
    _scheduled_tasks.remove(task)

    _log.info(f"Cancelling task {task['task']} created on {task['created']}")
    task["cancel_fn"]()
