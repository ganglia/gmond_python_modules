python-memcached-gmond
======================


This is a Python Gmond module for Memcached, compatible with both Python 2 and
3. In addition to the usual datapoints provided by "stats", this module
aggregates max age metrics from "stats items". All metrics are available in a
"memcached" collection group.

If you've installed ganglia at the standard locations, you should be able to
install this module by copying `memcached.pyconf` to `/etc/ganglia/conf.d` and
`memcached.py`, `memcached_metrics.py`, and 'every.py' to
`/usr/lib/ganglia/python_modules`. The memcached server's host and port can be
specified in the configuration in memcached.pyconf.

For more information, see the section [Gmond Python metric modules][1] in the
Ganglia documentation.

Author: Ori Livneh <ori@wikimedia.org>

  [1]: http://sourceforge.net/apps/trac/ganglia/wiki/ganglia_gmond_python_modules
