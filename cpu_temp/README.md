# cpu_temp

Python module for ganglia

It reads temperature from /sys/devices/platform/coretemp.*/

So, you need to insert the `coretemp` kernel module. <https://www.kernel.org/doc/Documentation/hwmon/coretemp>

Usually, the command is `modprob coretemp`.
