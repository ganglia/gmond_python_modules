# -*- coding:utf-8 -*-
import logging

import mysql.connector

logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/mysqlstats.log', filemode='w')
logging.debug('starting up')

from python_modules.packages.metrics import throughput_metrics
from python_modules.packages.metrics import count_metrics
from python_modules.packages.metrics import static_metrics
collectTemple 	= (throughput_metrics,count_metrics,static_metrics)
descriptors		= list()
variables	 	= {}
status		 	= {}



def get_status(name):
	"""return a metric value."""
	if name in throughput_metrics:
		name2key = name[6:-11].lower()
		if not name.startswith("mysql"):
			name2key = name[:-11].lower()
		return status[name2key]
	elif name in count_metrics:
		name2key = name[6:].lower()
		if not name.startswith("mysql"):
			name2key = name.lower()
		return status[name2key]
	elif name in static_metrics:
		name2key = name[6:].lower()
		if not name.startswith("mysql"):
			name2key = name.lower()
		return variables[name2key]
	# if name in count_metrics:
	# 	return status[name[7:].lower()]

def metric_init(params):
	"""Initialize all necessary initialization here."""
	global descriptors
	global metricsDefination
	global variables
	global status

	# 检查params
	if "host" not in params:
		logging.debug("找不到host定义.检查Jmysql.pyconf")
		exit(1)
	if "user" not in params:
		logging.debug("找不到user定义.检查Jmysql.pyconf")
		exit(1)
	if "passwd" not in params:
		logging.debug("passwd.检查Jmysql.pyconf")
		exit(1)

	# 连接mysql，获取状态
	conn = mysql.connector.connect(host=params["host"],
								 user=params["user"],
								 password=params["passwd"])
	cursor = conn.cursor()

	cursor.execute("show global variables;")
	variables.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
	cursor.execute("show global status;")
	status.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
	cursor.close()
	conn.close()

	for collect in collectTemple:
		for metric in collect:
			# 定义标准description
			d = dict(call_back	= get_status,
					 time_max	= 30,
					 value_type	= "uint",
					 units		= "",
					 format		= "%s",
					 slope		= "both")
			d.update(collect[metric])
			d.update({"name":metric})
			d.update({"title":metric})
			logging.debug("generated"+metric)
			descriptors.append(d)

	# print(status)
	return descriptors

def metric_cleanup():
	"""Clean up the metric module"""
	logging.shutdown()

if __name__ == "__main__":
	params = dict(host="192.168.1.104",
				  user="autop",
				  passwd="autop")
	metric_init(params)
	for d in descriptors:
		value = d["call_back"](d["name"])
		print("%-40s:%10s %-3s" %(d["name"],value,d["units"]))
	# print(descriptors)