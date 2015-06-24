# -*- coding:utf-8 -*-
import mysql.connector

descriptors		= list()
variables	 	= {}
status		 	= {}

from packages.metrics import throughput_metrics
from packages.metrics import count_metrics
from packages.metrics import static_metrics

def get_status(name):
	"""return a metric value."""
	if name in throughput_metrics:
		name2key = name[6:-11].lower()
		if not name.startswith("mysql"):
			name2key = name[:-11].lower()
		return status[name2key]
	# elif name in count_metrics:
	# 	name2key = name[6:].lower()
	# 	if not name.startswith("mysql"):
	# 		name2key = name.lower()
	# 	return status[name2key]
	# elif name in static_metrics:
	# 	name2key = name[6:].lower()
	# 	if not name.startswith("mysql"):
	# 		name2key = name.lower()
	# 	return variables[name2key]
	# return status["tokudb_txn_commits"]

def metric_init(params):
	"""Initialize all necessary initialization here."""
	global descriptors
	global metricsDefination
	global variables
	global status

	# 检查params
	if "host" not in params:
		print("找不到host定义.检查Jmysql.pyconf")
		exit(1)
	if "user" not in params:
		print("找不到user定义.检查Jmysql.pyconf")
		exit(1)
	if "passwd" not in params:
		print("passwd.检查Jmysql.pyconf")
		exit(1)

	# 连接mysql，获取状态
	conn = mysql.connector.connect(host=params["host"],
								 user=params["user"],
								 password=params["passwd"])
	cursor = conn.cursor()

	cursor.execute("show global variables;")
	# 初始化variables全局变量
	variables.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
	cursor.execute("show global status;")
	# 初始化status全局变量
	status.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
	cursor.close()
	conn.close()

	d1 = dict(name="tokudb_txn_commits_per_second",
			  call_back=get_status,
			  time_max=30,
			  value_type="uint",
			  units="N",
			  slope="both",
			  format="%u",
			  description="test metric")
	d2 = dict(name="tokudb_txn_aborts_per_second",
			  call_back=get_status,
			  time_max=30,
			  value_type="uint",
			  units="N",
			  slope="both",
			  format="%u",
			  description="test metric")
	descriptors.append(d1)
	descriptors.append(d2)
	# print(status)
	return descriptors

def metric_cleanup():
	"""Clean up the metric module"""
	# logging.shutdown()
	pass


if __name__ == "__main__":
	params = dict(host="192.168.1.104",
				  user="autop",
				  passwd="autop")
	metric_init(params)
	for d in descriptors:
		value = d["call_back"](d["name"])
		print("%-40s:%10s %-3s" %(d["name"],value,d["units"]))
	# print(descriptors)