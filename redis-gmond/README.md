ganglia-redis(7) -- Redis in Ganglia
====================================

## SYNOPSIS

Place `redis.py` and `redis.pyconf` in the appropriate directories and restart `gmond`(1).

## DESCRIPTION

Redis plugin for Ganglia that exposes most of the counters in the Redis `INFO` command to Ganglia for all your graphing needs.  The metrics it comes with are pretty rudimentary but they get the job done.

## FILES

* `/etc/ganglia/conf.d/modpython.conf`:
  Configures Ganglia for Python plugins.
* `/usr/lib/ganglia/python_modules/redis.py`:
  Redis plugin.
* `/etc/ganglia/conf.d/redis.pyconf`:
  Redis plugin configuration.

## THEME SONG

The Arcade Fire - "Wake Up"

## AUTHOR

Richard Crowley <richard@devstructure.com>

## SEE ALSO

`gmond`(1), the Ganglia monitor.

The Redis `INFO` command is described at <http://code.google.com/p/redis/wiki/InfoCommand>.

The original blog post on this plugin is at <http://rcrowley.org/2010/06/24/redis-in-ganglia.html>.  Gil Raphaelli's MySQL plugin, on which this one is based can be found at <http://g.raphaelli.com/2009/1/5/ganglia-mysql-metrics>.
