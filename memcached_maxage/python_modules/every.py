#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Every

    Python decorator; decorated function is called on a set interval.

    :author: Ori Livneh <ori@wikimedia.org>
    :copyright: (c) 2012 Wikimedia Foundation
    :license: GPL, version 2 or later
"""
from __future__ import division
from datetime import timedelta
import signal
import sys
import threading


# pylint: disable=C0111, W0212, W0613, W0621


__all__ = ('every', )


def total_seconds(delta):
    """
    Get total seconds of timedelta object. Equivalent to
    timedelta.total_seconds(), which was introduced in Python 2.7.
    """
    us = (delta.microseconds + (delta.seconds + delta.days * 24 * 3600) * 10**6)
    return us / 1000000.0


def handle_sigint(signal, frame):
    """
    Attempt to kill all child threads and exit. Installing this as a sigint
    handler allows the program to run indefinitely if unmolested, but still
    terminate gracefully on Ctrl-C.
    """
    for thread in threading.enumerate():
        if thread.isAlive():
            thread._Thread__stop()
    sys.exit(0)


def every(*args, **kwargs):
    """
    Decorator; calls decorated function on a set interval. Arguments to every()
    are passed on to the constructor of datetime.timedelta(), which accepts the
    following arguments: days, seconds, microseconds, milliseconds, minutes,
    hours, weeks. This decorator is intended for functions with side effects;
    the return value is discarded.
    """
    interval = total_seconds(timedelta(*args, **kwargs))
    def decorator(func):
        def poll():
            func()
            threading.Timer(interval, poll).start()
        poll()
        return func
    return decorator


def join():
    """Pause until sigint"""
    signal.signal(signal.SIGINT, handle_sigint)
    signal.pause()


every.join = join
