#!/usr/bin/python
import sys,os
descriptors = list()

def call_back(name):
	"""return a metric value."""
	return name

def metric_init(params):
	"""Initialize all necessary initialization here."""
	global descriptors

	if "param1" in params:
		p1 = params["param1"]
	d1 = dict(name="jianqiaoMetric", call_back=call_back, time_max=30, value_type="unit", units='N', slope="both",
			  format="%u", description="jianqiaoMetric4mysql", groups="example")
	# print(d1)

	descriptors = [d1]
	return descriptors

def metric_cleanup():
	"""Clean up the metric module"""
	pass

if __name__ == "__main__":
	params = {"param1":"param1_value"}
	metric_init(params)
	for d in descriptors:
		value = d["call_back"](d["name"])
		print("value for %s is %s" %(d["name"],value))