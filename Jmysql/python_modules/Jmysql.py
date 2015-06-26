# -*- coding:utf-8 -*-
import mysql.connector
import json,sys,os,time
import logging


from packages.metrics import throughput_metrics
from packages.metrics import count_metrics
from packages.metrics import static_metrics
from packages.metrics import test_metrics
from packages.metrics import almost_real_metrics


descriptors		= list()
variables	 	= {}
now_status		= {}
last_status		= {}
last_update		= 0
TIME_INTERVAL	= 15

testNum			= 0


logging.basicConfig(level=logging.DEBUG,
                    format='%(process)d-%(threadName)s-%(asctime)s-%(filename)s[line:%(lineno)d]-%(levelname)s-%(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='/tmp/test.log',
                    filemode='w')
logging.debug('starting up')

def get_status(name):
	"""return a metric value."""
	global variables
	global now_status
	global last_status
	global last_update

	now = time.time()
	delt = now - last_update
	if delt<TIME_INTERVAL:
		logging.debug("%-40s <<<<<<<<" %name)
	else:
		logging.debug("%-40s >>>>>>>>" %name)
		logging.debug("%-40s 更新last_update" %name)
		last_update = now
		logging.debug("%-40s 更新last_status" %name)
		last_status.update(now_status)
		logging.debug("%-40s last_status Com_select %s" %(name,last_status["Com_select"]))
		# 获取当前状态
		# now_status全局变量
		logging.debug("%-40s 数据库操作" %name)
		cursor.execute("show global status;")
		logging.debug("%-40s 更新now_status" %name)
		now_status.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
		logging.debug("%-40s now_status Com_select %s" %(name,now_status["Com_select"]))

	logging.debug("name:%-40s | nowTime:%s | delt:%s" %(name,now,delt))

	# 返回metrics值
	if name in throughput_metrics:
		name2key = name[6:-11].lower()
		if not name.startswith("mysql"):
			name2key = name[:-11].lower()
		# return int(now_status[name2key])
		nowV = float(now_status[name2key])
		oldV = float(last_status[name2key.decode('utf-8')].encode("utf-8"))
		logging.debug("name:%-40s | nowV:%s | oldV:%s" %(name,nowV,oldV))
		result = nowV-oldV
		return result
	elif name in count_metrics:
		name2key = name[6:].lower()
		if not name.startswith("mysql"):
			name2key = name.lower()
		return int(now_status[name2key])
	elif name in static_metrics:
		name2key = name[6:].lower()
		if not name.startswith("mysql"):
			name2key = name.lower()
		return int(variables[name2key])
	global testNum
	if name == "test_metric0":
		testNum+=2
		return testNum

def metric_init(params):
	"""Initialize all necessary initialization here."""
	global descriptors
	global variables
	global now_status

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
	# 初始化variables全局变量
	cursor.execute("show global variables;")
	variables.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
	# 初始化status全局变量
	cursor.execute("show global status;")
	now_status.update(dict(((k.lower().encode("utf-8"), v.encode("utf-8")) for (k,v) in cursor)))
	logging.debug("开始")
	# for collect in (throughput_metrics,count_metrics,static_metrics):
	for collect in (throughput_metrics,):
	# for collect in (almost_real_metrics,):
	# for collect in (test_metrics,):
		for metric in collect:
			d0 = dict(call_back=get_status,
					  time_max=15,
					  value_type="uint",
					  units="N",
					  slope="both",
					  format="%u",
					  GROUP="Jmysql",
					  description="test metric"
					  )
			d0.update(collect[metric])

			descriptors.append(d0)
	return descriptors

def metric_cleanup():
	"""Clean up the metric module"""
	cursor.close()
	conn.close()
	logging.shutdown()
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
	else:
		metric_init(params)
		for d in descriptors:
			print("%-40s value is %s" %(d["name"],d["call_back"](d["name"])))
		metric_cleanup()