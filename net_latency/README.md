Net Latency
===========
A python module for Ganglia Monitoring System.

This module measures the network latency of a host using ping. By default, the module pings the host's gateway and measures the round-trip time in microseconds.

#Configuration

The module uses the following parameters that are defined in the file "net_latency.pyconf".

-refresh_rate: Specify the module's refresh rate in seconds. The default is 10s.
-target: You can change the ping target by specifying here a custom address.

#Dependencies
This module depends on the following libraries and tools:

-ping

#Author
Giorgos Kappes <contact@giorgoskappes.com>
