#!/usr/bin/env python
# -*- coding:utf-8 -*-
# author:jianqiao.ms




# import json
# f = open("last_status","wb")
# str = json.load(f)
# print(str)
# print(type(str))
# f.close()

# import mysql.connector
# import json
#
# conn = mysql.connector.connect(user="cupid",
#                                password="everyone2xhfz",
#                                host="192.168.1.104")
# cursor = conn.cursor()
#
# # cursor.execute("SHOW global status like \'Com_select\';")
# # for line in cursor:
# #     print(line)
# # print("=================================================")
# print(dir(cursor))
# # cursor.execute("SHOW global status;")
# # metricList = cursor.fetchall()
# # conn.close()
# # metricDict = {}
# # print(metricList)
# # for m in metricList:
# #     metricDict[m[0].encode("utf-8")]=m[1].encode("utf-8")
# #
# # f.write(json.dumps(metricDict))
# # f.close()
# # print(metricDict)
#
#
# cursor.execute("SHOW VARIABLES")
# print(cursor.fetchall)
# #variables = dict(((k.lower(), v) for (k,v) in cursor))
# variables = {}
# for (k,v) in cursor:
#     variables[k.lower()] = v
#
# # print(variables)
# try:
#     raise Exception("test")
# except Exception,e:
#     print(e.message)

a = {"a":"","b":"123","c":"ccc"}
b = {"a":"aaa","b":"456"}
a.update(b)
print(a)