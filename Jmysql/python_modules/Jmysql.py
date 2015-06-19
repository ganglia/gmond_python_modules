#!/usr/bin/python
# -*- coding:utf-8 -*-
import sys,os

import logging
logging.basicConfig(level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s\t Thread-%(thread)d - %(message)s", filename='/tmp/mysqlstats.log', filemode='w')
logging.debug('starting up')

from metrics import throughput_metrics
from metrics import count_metrics
from metrics import static_metrics

descriptors 		= list()
metricTemple 		= (throughput_metrics,count_metrics,static_metrics)

def get_status(name):
	"""return a metric value."""
	return name

def metric_init(params):
	"""Initialize all necessary initialization here."""
	global descriptors
	global metricsDefination

	# 检查params
	if "host" in params:
		host = params["host"]
	else:
		logging.debug("找不到host定义.检查Jmysql.pyconf")
		exit(1)
	if "user" in params:
		user = params["user"]
	else:
		logging.debug("找不到user定义.检查Jmysql.pyconf")
		exit(1)
	if "passwd" in params:
		passwd = params["passwd"]
	else:
		logging.debug("passwd.检查Jmysql.pyconf")
		exit(1)

	for metrics in metricTemple:
		for defination in metrics:
			# 定义标准description
			d = dict(call_back	= get_status,
					 time_max	= 30,
					 value_type	= "unit",
					 units		= "",
					 format		= "%s",
					 slope		= "both")
			d.update(metrics[defination])
			d.update({"name":defination})
			logging.debug("generated"+defination)
			descriptors.append(d)

	return descriptors

def metric_cleanup():
	"""Clean up the metric module"""
	pass

if __name__ == "__main__":
	params = dict(host="192.168.1.104",
				  user="autop",
				  passwd="autop")
	metric_init(params)
	# for d in descriptors:
	# 	value = d["call_back"](d["name"])
	# 	print("value for %s is %s" %(d["name"],value))
	print(descriptors)