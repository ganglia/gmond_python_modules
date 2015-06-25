#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author:jianqiao.ms

static = """###
### Note:
###   To setup database access:
###   GRANT SUPER, PROCESS ON *.* TO 'autop'@'%' IDENTIFIED BY "autop";
###
###   Notice in this example binlogging is not enabled in the MySQL
###   server. In this case the "mysql_binlog_*" metrics are
###   commented out.
###

modules {
    module {
        name = "Jmysql"
        language = "python"

        param host {
            value = '127.0.0.1'
        }
        param user {
            value = 'autop'
        }
        param passwd {
            value = 'autop'
        }
    }
}
"""

fp = open("../conf.d/Jmysql.pyconf","w+")
#fp.close()

from packages.metrics import throughput_metrics
from packages.metrics import count_metrics
from packages.metrics import static_metrics

fp.write(static+"\n")

fp.write("collection_group {\n")
fp.write("\tcollect_every = 30\n")
fp.write("\ttime_threshold = 30\n\n")
for key in throughput_metrics:
    fp.write("\tmetric {\n")
    fp.write("\t\tname = \"%s\"\n" %key)
    fp.write("\t}\n")
fp.write("}\n\n")

fp.write("collection_group {\n")
fp.write("\tcollect_every = 30\n")
fp.write("\ttime_threshold = 30\n\n")
for key in count_metrics:
    fp.write("\tmetric {\n")
    fp.write("\t\tname = \"%s\"\n" %key)
    fp.write("\t}\n")
fp.write("}\n\n")

fp.write("collection_group {\n")
fp.write("\tcollect_once = yes\n")
fp.write("\ttime_threshold = 30\n\n")
for key in static_metrics:
    fp.write("\tmetric {\n")
    fp.write("\t\tname = \"%s\"\n" %key)
    fp.write("\t}\n")
fp.write("}\n")

fp.close()