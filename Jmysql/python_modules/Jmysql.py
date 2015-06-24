# -*- coding:utf-8 -*-
import mysql.connector
import json,sys,os

descriptors		= list()
variables	 	= {}
status		 	= {}
lastStatus		= {}
statusFile 		= os.path.join(os.path.dirname(__file__),"last_status")

from packages.metrics import throughput_metrics
from packages.metrics import count_metrics
from packages.metrics import static_metrics

def get_status(name):
	"""return a metric value."""
	if name in throughput_metrics:
		name2key = name[6:-11].lower()
		if not name.startswith("mysql"):
			name2key = name[:-11].lower()
		# return status[name2key]
		now = int(status[name2key])
		old = int(lastStatus[name2key.decode('utf-8')].encode("utf-8"))
		result = (now-old)/30
		# print(name)
		# print("now:%u" %now)
		# print("old:%u" %old)
		# print("result:%u" %result)
		# print("________________________________________________________________")
		return result

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
	return status["tokudb_txn_commits"]

def metric_init(params):
	"""Initialize all necessary initialization here."""
	global descriptors
	global variables
	global status
	global lastStatus

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

	# 从文件中获取json数据
	fp=open(statusFile,"r")
	lastStatus = json.load(fp)
	fp.close()

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

	for collect in (throughput_metrics,count_metrics,static_metrics):
		for metric in collect:
			d0 = dict(call_back=get_status,
					  time_max=30,
					  value_type="uint",
					  units="N",
					  slope="both",
					  format="%u",
					  group="Jmysql",
					  description="test metric")
			d0.update(collect[metric])
			# print(d0)
			descriptors.append(d0)
	return descriptors

def metric_cleanup():
	"""Clean up the metric module"""
	# pass
	global status
	fp = open(statusFile,"w")
	fp.write(json.dumps(status))
	fp.close()

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
			# d["call_back"](d["name"])
			print("%s value is %s" %(d["name"],d["call_back"](d["name"])))
		metric_cleanup()
