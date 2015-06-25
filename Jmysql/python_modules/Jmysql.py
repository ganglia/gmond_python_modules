# -*- coding:utf-8 -*-
import mysql.connector
import json,sys,os

descriptors		= list()
variables	 	= {}
now_status		= {}
last_Status		= {}
statusFile 		= os.path.join(os.path.dirname(__file__),"last_status")
testNum			= 0

from packages.metrics import throughput_metrics
from packages.metrics import count_metrics
from packages.metrics import static_metrics
from packages.metrics import test_metrics

def get_status(name):
	"""return a metric value."""
	# global status
    #
	# # 获取当前状态
	# # 初始化variables全局变量
	# cursor.execute("show global variables;")
	# variables.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
	# # 初始化status全局变量
	# cursor.execute("show global status;")
	# status.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
    #
	# # 返回metrics值
	# if name in throughput_metrics:
	# 	name2key = name[6:-11].lower()
	# 	if not name.startswith("mysql"):
	# 		name2key = name[:-11].lower()
	# 	return int(status[name2key])
	# 	# now = float(status[name2key])
	# 	# old = float(lastStatus[name2key.decode('utf-8')].encode("utf-8"))
	# 	# result = (now-old)/30
	# 	# return result
	# elif name in count_metrics:
	# 	name2key = name[6:].lower()
	# 	if not name.startswith("mysql"):
	# 		name2key = name.lower()
	# 	return int(status[name2key])
	# elif name in static_metrics:
	# 	name2key = name[6:].lower()
	# 	if not name.startswith("mysql"):
	# 		name2key = name.lower()
	# 	return int(variables[name2key])
	global testNum
	if name == "test_metric0":
		testNum+=2
		return testNum
	# if name == "test_metric1":
	# 	testNum+=3
	# 	return testNum

def metric_init(params):
	"""Initialize all necessary initialization here."""
	global descriptors
	global variables
	global status

	global conn
	global cursor

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

	# 连接mysql
	conn = mysql.connector.connect(host=params["host"].encode("utf-8"),
								   user=params["user"].encode("utf-8"),
								   password=params["passwd"].encode("utf-8"))
	cursor = conn.cursor()

	# for collect in (throughput_metrics,count_metrics,static_metrics):
	for collect in (test_metrics,):
		for metric in collect:
			d0 = dict(call_back=get_status,
					  time_max=30,
					  value_type="uint",
					  units="N",
					  slope="both",
					  format="%u",
					  group="Jmysql",
					  description="test metric",
					  test="100")
			d0.update(collect[metric])

			descriptors.append(d0)
	return descriptors

def metric_cleanup():
	"""Clean up the metric module"""
	cursor.close()
	conn.close()
	# pass


if __name__ == "__main__":
	params = dict(host="192.168.1.104",
				  user="autop",
				  passwd="autop")
	if "--init" in sys.argv:
		status = {}
		conn = mysql.connector.connect(host=params["host"],
								 user=params["user"],
								 password=params["passwd"])
		cursor = conn.cursor()
		cursor.execute("show global status;")
		status.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
		cursor.close()
		conn.close()
		fp = open("last_status","w")
		fp.write(json.dumps(status))
		fp.close()
	else:
		metric_init(params)
		for d in descriptors:
			print("%-40s value is %s" %(d["name"],d["call_back"](d["name"])))
		metric_cleanup()
