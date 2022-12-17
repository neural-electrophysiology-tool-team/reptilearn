"""
Task scheduling of dynamically loaded task functions.
Author: Tal Eisenberg, 2021

The config module attribute `tasks_modules_dir` determines where tasks will be loaded from. Any
non-private function (which does not start with an underscode _) that is defined in a module inside
this directory will be added to the task list.

Task functions can not accept any arguments.

Tasks are scheduled using the schedule module and use the schedule pool "__tasks__"
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
    """
    Initialize module. Find all available task functions.
    """
    global _log
    _log = get_main_logger()

    all_tasks()


def all_tasks():
    """
    Load all modules in the tasks modules directory, and find every task function
    in these modules. The available tasks are stored in global variables.
    """
    global _tasks, _task_modules, _task_names

    _tasks = {}
    _task_modules = load_modules(get_config().tasks_modules_dir, _log)
    _task_names = {}

    for k, (m, s) in _task_modules.items():
        _tasks[k] = _module_tasks(m)
        _task_names[k] = list(_tasks[k].keys())

    return _task_names


def _module_tasks(module):
    public_fns = dict(
        (
            (name, func)
            for name, func in inspect.getmembers(module)
            if not name.startswith("_") and callable(func) and type(func) is not type and func.__module__ == module.__name__
        )
    )
    return public_fns


def _get_new_scheduled_task_id():
    global _last_scheduled_task_id
    _last_scheduled_task_id += 1
    return _last_scheduled_task_id


def scheduled_tasks():
    """
    Return a list of dictionaries describing every currently scheduled task.
    Each dict contains the following keys:
    - task: str. the task module and function name separated by a dot (e.g. module.fn).
    - task_type: str. the task schedule type. See schedule_task.
    - params: dict. the parameters used to schedule this task. See schedule_task.
    - created: datetime. task creation timestamp.
    - task_id: a unique task id.
    """
    return [
        {k: v for k, v in t.items() if k != "cancel_fn"}
        for t in _scheduled_tasks
        if sched.is_scheduled(t["cancel_fn"], pool=_task_pool)
    ]


def run(module, task):
    """
    Run a task function.

    NOTE: Only tasks that were previously found by calling all_tasks() can be run.

    Args:
    - module: str. the task module name.
    - task: str. the task function name.
    """
    if module not in _tasks:
        raise Exception(f"Unknown task module: {module}")

    if task not in _tasks[module]:
        raise Exception(f"Unknown task {task} in module {module}.")

    _tasks[module][task]()


def schedule_task(module, task, task_type, **kwargs):
    """
    Schedule a task to run at specific times.

    There are three possible schedule types, determined by the `task_type` argument:
    - datetime: Schedule using `schedule.on_datetime` to run at a specific datetime.
                Parameters:
                - dt: Either a datetime object or a datetime parsable string.
    - interval: Schedule using `schedule.repeat` to run in `interval` seconds possibly repeatedly.
                Parameters:
                - interval: The schedule interval in seconds.
                - repeats: The number of repeats of the schedule or True to repeat until cancelled.
    - timeofday: Schedule using `schedule.timeofday` to run at a specific time of day possible repeatedly.
                Parameters:
                - dt: Either a datetime object or a datetime parsable string. Only the time of the datetime is used.
                - repeats: The number of repeats of the schedule or True to repeat until cancelled.

    For more information see the corresponding schedule function in the schedule module.

    Args:
    - module: str. The task module name.
    - task: str. The task function name.
    - task_type: str. One of "datetime", "interval", "timeofday".
    """
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
            "task_id": _get_new_scheduled_task_id(),
        }
    )


def cancel_task(task_id):
    """
    Cancel a task schedule with the supplied `task_id` unique id.
    The id should be the same as one of the `task_id`s in the list returned by `scheduled_tasks()`

    Args:
    - task_id: a unique scheduled task id.
    """
    tasks = [t for t in _scheduled_tasks if t["task_id"] == task_id]
    if len(tasks) == 0:
        raise ValueError(f"Unknown task_id: {task_id}")
    task = tasks[0]
    _scheduled_tasks.remove(task)

    _log.info(f"Cancelling task {task['task']} created on {task['created']}")
    task["cancel_fn"]()
