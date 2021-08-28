"""
schedule: Functions for running tasks at various schedules.
Author: Tal Eisenberg, 2021
"""

from datetime import datetime, time, timedelta
import threading
import logging
import functools
from collections import Sequence

_log = logging.getLogger("Main")
_cancel_fns = {}


def schedule_func(thread_fn):
    """
    Return a schedule function that will run thread_fn in a separate thread.
    - thread_fn: A function with signature
                    (callback, args, kwargs, cancel_event, *sch_args, **sch_kwargs)
        The thread_fn needs to invoke the callback at some future time. When
        the cancel_event (threading.Event) is set the thread should finish.

        - callback: The task function that will be scheduled.
        - args, kwargs: The task arguments list and named arguments dictionary.
        - cancel_event: threading.Event that will be set when the schedule should be cancelled.
        - pool: The task pool name.
        - *sch_args, **sch_kwargs: arguments and named-arguments of the schedule function.

    The returned schedule function has this signature:
        (callback, *sch_args, args=(), kwargs={}, **sch_kwargs)

        These are the same arguments as in thread_fn except for the cancel_event.

        The schedule function returns a function that cancels the schedule, the
        cancel function is added to the task pool named by the pool argument.
    """

    @functools.wraps(thread_fn)
    def sched_fn(
        callback, *sch_args, args=(), kwargs={}, pool="experiment", **sch_kwargs
    ):
        cancel_event = threading.Event()

        def cancel():
            cancel_event.set()

        def target():
            if pool not in _cancel_fns:
                _cancel_fns[pool] = []
            _cancel_fns[pool].append(cancel)

            try:
                thread_fn(callback, args, kwargs, cancel_event, *sch_args, **sch_kwargs)
                name = threading.current_thread().name
                if cancel_event.is_set():
                    _log.debug(f"{name}: Schedule cancelled")
                else:
                    _log.debug(f"{name}: Schedule finished")

            finally:
                _cancel_fns[pool].remove(cancel)
                if len(_cancel_fns[pool]) == 0:
                    del _cancel_fns[pool]

        threading.Thread(target=target).start()
        return cancel

    return sched_fn


def cancel_all(pool="experiment"):
    """
    Cancel all scheduled tasks in the supplied task pool.

    pool: string, the task pool name.
    """

    if pool is None:
        for p in _cancel_fns.keys():
            cancel_all(p)
        return

    if pool not in _cancel_fns:
        raise ValueError("Pool doesn't exist")

    fns = list(_cancel_fns[pool])
    for f in fns:
        f()


def is_scheduled(cancel_fn, pool="experiment"):

    return pool in _cancel_fns and cancel_fn in _cancel_fns[pool]


def replace_timeofday(base: datetime, timeofday: time):
    """Replace the time of the base datetime to the timeofday time."""
    t = timeofday
    return base.replace(
        hour=t.hour, minute=t.minute, second=t.second, microsecond=t.microsecond
    )


def next_timeofday(base: datetime, timeofday: time):
    """
    Return a datetime pointing to the next occurrence of the specified
    timeofday, either the same day as base or the next day.
    base - a datetime object
    timeofday - a time object
    """
    same_day = replace_timeofday(base, timeofday)
    if same_day - base < timedelta(0):
        return same_day + timedelta(days=1)
    else:
        return same_day


@schedule_func
def once(callback, args, kwargs, cancel_event, interval):
    """
    Signature:

    once(callback, interval, pool='experiment', args=(), kwargs={})

    Schedule <callback> to run once after <interval> seconds passed.

    args, kwargs - Arguments that will be passed to the callback function as non-keyword,
                   and keyword arguments respectively.

    Return a cancel() function that cancels the schedule once called."""
    if interval is None or interval == 0:
        callback(*args, **kwargs)
    else:
        cancel_event.wait(interval)
        if not cancel_event.is_set():
            callback(*args, **kwargs)


@schedule_func
def repeat(callback, args, kwargs, cancel_event, interval, repeats=True):
    """
    Signature:

        repeat(callback, interval, repeats=True, pool='experiment', args=(), kwargs={})

    Schedule <callback> to run repeatedly every <interval> seconds.

    repeats - True: repeat the schedule until cancelled.
              int: number of times to repeat the schedule.

    args, kwargs - Arguments that will be passed to the callback function as non-keyword,
                   and keyword arguments respectively.

    Return a cancel() function that cancels the schedule once called.
    """
    repeat_count = 0

    while True:
        cancel_event.wait(interval)
        if not cancel_event.is_set():
            callback(*args, **kwargs)
        else:
            break

        repeat_count += 1
        if repeats is not True and repeat_count >= repeats:
            break


@schedule_func
def timeofday(callback, args, kwargs, cancel_event, timeofday, repeats=1):
    """
    Signature:

        timeofday(callback, timeofday, repeats=1, pool='experiment', args=(), kwargs={})

    Schedule <callback> to run at the next <timeofday>, possibly repeating every 24 hours.

    timeofday - Either a datetime.time instance or a sequence of arguments passed to the
                datetime.time initializer.
    repeats - True: The schedule will run the task at the specified time of day until cancelled.
              int: The number of times the task will be repeated.
    args, kwargs - Arguments that will be passed to the callback function as non-keyword,
                   and keyword arguments respectively.

    Return a cancel() function that cancels the schedule once called.
    """
    if not isinstance(timeofday, time):
        if isinstance(timeofday, Sequence):
            timeofday = time(*timeofday)
        else:
            raise TypeError(f"Invalid timeofday type ({type(timeofday)})")

    repeat_count = 0
    start_time = datetime.now()
    first_sched = next_timeofday(start_time, timeofday)
    interval = (first_sched - start_time).total_seconds()

    while True:
        cancel_event.wait(interval)
        if not cancel_event.is_set():
            callback(*args, **kwargs)
        else:
            break

        repeat_count += 1
        if repeats is not True and repeat_count >= repeats:
            break

        tomorrow = datetime.now() + timedelta(days=1)
        next_time = replace_timeofday(tomorrow, timeofday)
        interval = (next_time - datetime.now()).total_seconds()


@schedule_func
def on_datetime(callback, args, kwargs, cancel_event, dt):
    """
    Signature:

        on_datetime(callback, dt, pool='experiment', args=(), kwargs={})

    Schedule <callback> to run at the date and time of dt.

    dt - A datetime instance.
    args, kwargs - Arguments that will be passed to the callback function as non-keyword,
                   and keyword arguments respectively.

    Return a cancel() function that cancels the schedule once called.
    """
    if not isinstance(dt, datetime):
        raise TypeError(f"Invalid dt type. ({type(dt)})")

    interval = (dt - datetime.now().astimezone()).total_seconds()

    if interval < 0:
        raise Exception(f"Datetime is in the past ({interval} seconds).")

    cancel_event.wait(interval)
    if not cancel_event.is_set():
        callback(*args, **kwargs)


@schedule_func
def sequence(callback, args, kwargs, cancel_event, intervals: Sequence, repeats=1):
    """
    Signature:

        sequence(callback, intervals: Sequence, repeats=1, pool='experiment', args=(), kwargs={})

        Run the callback at a sequence of intervals, possibly repeating the sequence once
        it's finished.

        intervals - A sequence of intervals in seconds. The schedule will wait the i-th
                    interval before the i-th invocation of the callback.
        repeats - True: repeat the scheduled sequence until cancelled.
                  int: number of times to repeat the whole sequence.

        args, kwargs - Arguments that will be passed to the callback function as non-keyword,
                       and keyword arguments respectively.

        Return a cancel() function that cancels the schedule once called.
    """

    cur_interval = 0
    repeat_count = 0

    while True:
        cancel_event.wait(intervals[cur_interval])
        if not cancel_event.is_set():
            callback(*args, **kwargs)
        else:
            break

        cur_interval += 1
        if cur_interval >= len(intervals):
            cur_interval = 0
            repeat_count += 1
            if repeats is not True and repeat_count >= repeats:
                break
