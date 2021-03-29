from datetime import datetime, time, timedelta
import threading
import logging
from collections import Sequence

# one-shot timer, repeating timer, time of day scheduling (thread based)

log = logging.getLogger("Main")
cancel_fns = []


def _gen_schedule_fn(thread_fn):
    def sched_fn(callback, *args, **kwargs):
        cancel_event = threading.Event()

        def cancel():
            cancel_event.set()

        def target():
            cancel_fns.append(cancel)
            try:
                thread_fn(callback, cancel_event, *args, **kwargs)
            except Exception as e:
                cancel_fns.remove(cancel)
                raise e

            name = threading.current_thread().name
            if cancel_event.is_set():
                log.debug(f"{name}: Schedule cancelled")
            else:
                log.debug(f"{name}: Schedule finished")

            cancel_fns.remove(cancel)

        threading.Thread(target=target).start()
        return cancel

    return sched_fn


def cancel_all():
    while len(cancel_fns) != 0:
        cancel_fns[0]()


def replace_timeofday(base: datetime, timeofday: time):
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


def sched_once(callback, cancel_event, interval):
    if interval is None or interval == 0:
        callback()
    else:
        cancel_event.wait(interval)
        if not cancel_event.is_set():
            callback()


def sched_repeat(callback, cancel_event, interval, repeats=True):

    repeat_count = 0

    while True:
        cancel_event.wait(interval)
        if not cancel_event.is_set():
            callback()
        else:
            break

        repeat_count += 1
        if repeats is not True and repeat_count >= repeats:
            break


def sched_timeofday(callback, cancel_event, timeofday, repeats=1):
    """repeats=None -> never stop"""
    if not isinstance(timeofday, time):
        if isinstance(timeofday, Sequence):
            timeofday = time(*timeofday)
        else:
            raise TypeError("Invalid timeofday type ({type(timeofday)})")

    repeat_count = 0
    start_time = datetime.now()
    first_sched = next_timeofday(start_time, timeofday)
    interval = (first_sched - start_time).total_seconds()

    while True:
        cancel_event.wait(interval)
        if not cancel_event.is_set():
            callback()
        else:
            break

        repeat_count += 1
        if repeats is not True and repeat_count >= repeats:
            break

        tomorrow = datetime.now() + timedelta(days=1)
        next_time = replace_timeofday(tomorrow, timeofday)
        interval = (next_time - datetime.now()).total_seconds()


def sched_sequence(callback, cancel_event, intervals: Sequence, repeats=1):
    cur_interval = 0
    repeat_count = 0

    while True:
        cancel_event.wait(intervals[cur_interval])
        if not cancel_event.is_set():
            callback()
        else:
            break

        cur_interval += 1
        if cur_interval >= len(intervals):
            cur_interval = 0
            repeat_count += 1
            if repeats is not True and repeat_count >= repeats:
                break


once = _gen_schedule_fn(sched_once)
repeat = _gen_schedule_fn(sched_repeat)
timeofday = _gen_schedule_fn(sched_timeofday)
sequence = _gen_schedule_fn(sched_sequence)
