celery
===============

Python module for ganglia 3.1.

This module allows you to collect from Celery Distributed Task Queue
from http://docs.celeryproject.org.

Prerequisite
============

Make sure Celery exposes it's API over HTTP e.g.

curl http://localhost:8989/api/worker/

or similar needs to succeed for this module to work.


Install
===============

Copy ganglia_celery.py from python_modules to your python modules directory e.g.

/usr/lib64/ganglia/python_modules

and celery.pyconf to

/etc/ganglia/conf.d/

Restart Gmond and you are done.

## AUTHOR

Author: Vladimir Vuksan https://github.com/vvuksan
