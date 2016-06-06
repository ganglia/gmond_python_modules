netstats
=====

Exports raw stats found in `/proc/net/netstat` and /proc/net/snmp`.

Install 
-------

Copy netstats.py from python_modules to your python modules directory, e.g. :

 - /usr/lib/ganglia/python_modules
 - /usr/lib64/ganglia/python_modules

Copy netstats.pyconf to the gmond conf.d directory, e.g. :

 - /etc/ganglia/conf.d/

Tune the netstats.pyconf file to match your needs and then restart gmond.

## AUTHOR

Author: Doychin Atanasov https://github.com/ironsmile