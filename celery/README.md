celery
===============

Python module for ganglia 3.1.

This module allows you to collect from Celery Distributed Task Queue
from http://docs.celeryproject.org.

Prerequisite
============

This version of the module works with Flower (https://github.com/mher/flower),
a web-based tool to monitor Celery workers and tasks.

Previous versions of this module worked with Celerymon, which has now been
obsoleted in favor of Flower (http://celery.readthedocs.org/en/latest/userguide/monitoring.html?highlight=flower#flower-real-time-celery-web-monitor).

Install
===============

Copy ganglia_celery.py from python_modules to your python modules directory e.g.

/usr/lib64/ganglia/python_modules

and celery.pyconf to

/etc/ganglia/conf.d/

Restart Gmond and you are done.

## AUTHOR

Author: Vladimir Vuksan https://github.com/vvuksan
