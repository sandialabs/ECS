#!/usr/bin/env python3

# Copyright 2021 National Technology & Engineering Solutions of Sandia, LLC (NTESS). 
# Under the terms of Contract DE-NA0003525 with NTESS, the U.S. Government retains 
# certain rights in this software.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# IMPORTS

import argparse
import configparser
import requests
import json
import logging
import http.client as http_client
import re
from datetime import datetime
import time

# FLAGS, GLOBALS

verbose = False
delay = False
ip = ''
port = 0
time_option = ''
log_file = ''
index = ''
username = ''
password = ''
security = False



# CONSOLE OUTPUT FUNCTIONS

def notify(message):
	global verbose
	if not verbose:
		return
	yellow='\033[0;33m'
	no_color='\033[0m'
	print(yellow + "[+] " + message + no_color)

def error(message):
	red='\033[0;31m'
	no_color='\033[0m'
	print(red + "[!] " + message + no_color)


# MAIN PROGRAM FUNCTIONS

def parse_logs(my_file):
	decoder = json.JSONDecoder()
	fileobj = open(my_file, 'r')
	#TODO:: verify log file content / structure?
	all_logs = []

	contents = fileobj.readlines()
	for line in contents:
		line=line.strip()
		pos = 0
		while not pos == len(line):
			curr_log, length = decoder.raw_decode(line[pos:])
			all_logs.append(curr_log)
			pos+=length

	#edge case where an empty string ends up in there
	while("" in all_logs):
		all_logs.remove("")

	return all_logs


#sample timestamp: 2022-12-09T19:14:25.412Z
#KEY ASSUMPTION = LOGS ARE INGESTED IN ORDER BY TIMESTAMP
def update_timestamps(logs, time_option):
	
	datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
	earliest_timestamp = ""
	earliest_datetime = None

	if time_option == 'no_update':
		return logs
	elif time_option == 'now':
		origin_datetime = datetime.now()
	elif re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z', time_option):
		origin_datetime = datetime.strptime(time_option, datetime_format)
	else:
		error("Time option not supported. See help for more details. Exiting . . .")
		exit(-1)


	notify("Updating timestamps using option: " + time_option)

	new_logs = []
	
	for i in logs:
		#I vehemently oppose this, but couldn't think of a faster way
		log_string = json.dumps(i)
		#finding strings that match format coming out of logstash and update - this supports winlogbeat format and possibly others
		result = re.finditer(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z', log_string)
		for j in result:
			if earliest_timestamp == "":
				earliest_timestamp = j.group(0)
			earliest_datetime = datetime.strptime(earliest_timestamp, datetime_format)
			current_datetime = datetime.strptime(j.group(0), datetime_format)
			time_delta = current_datetime - earliest_datetime
			new_datetime = origin_datetime + time_delta
			new_timestamp = new_datetime.strftime(datetime_format)
			new_timestamp = new_timestamp[:-4] + 'Z' #python is automatically printing microseconds, chop off 3 LSDs + the 'Z' (zulu) and re-add the Z
			log_string = log_string.replace(j.group(0), new_timestamp)
		#add @timestamp option in case of "ts" : "<epoch>" - this supports bro log format
		if "ts" in i:
			if isinstance(i["ts"], float):
				if earliest_datetime == None:
					earliest_datetime = datetime.fromtimestamp(i["ts"])
					earliest_timestamp = earliest_datetime.strftime(datetime_format)
				current_datetime = datetime.fromtimestamp(i["ts"])
				time_delta = current_datetime - earliest_datetime
				new_datetime = origin_datetime + time_delta
				new_timestamp = new_datetime.strftime(datetime_format)
				new_timestamp = new_timestamp[:-4] + 'Z' #python is automatically printing microseconds, chop off 3 LSDs + the 'Z' (zulu) and re-add the Z
				i["@timestamp"] = new_timestamp
				i["ts"] = new_datetime.strftime("%s.%f")
				log_string = json.dumps(i)
		if ( len(list(result)) > 0 ) and ("ts" in i):
			error("Provided log file has attributes of Zeek log dump and winlogbeat log dump. Exiting to avoid arbitrary behavior. . .")
			exit(-1)
		new_logs.append(json.loads(log_string))
	return new_logs

def send_logs(logs, ip, port, index):
	global security, username, password

	if(security):
		prot = "https://"
	else:
		prot = "http://"

	es_url = prot + ip + ":" + str(port) + "/_bulk/?pretty"

	headers = {
		'Content-Type': 'application/json',
	}
	
	actions = []
	for i in logs:
		actions.append("{\"index\": {\"_index\": \"" + index + "\"}}")
		actions.append(json.dumps(i))
	
	body='\n'.join(actions)

	#The bulk request must be terminated by a newline [\\n]
	body+="\n"

	#print(body)
	#return("stdout")

	response = requests.post(es_url, headers=headers, data=body, auth=(username, password), verify=False)
	return str(response)

def trickle_logs(logs, ip, port, index):
	notify("Trickling logs one by one according to timestamp.")

	datetime_format = "%Y-%m-%dT%H:%M:%S.%fZ"
	latest_datetime = None

	#get logs sorted by time
	logs.sort(key=lambda x: x["@timestamp"])

	#TODO:: if we want total fidelity we can take timestamps during the loop and then diff real time past with time delta in logs.... I assume this time is negligble for now.
	num = 0
	print(num)
	for i in logs:
		num+=1
		#body = "{\"index\": {\"_index\": \"" + index + "\"}}"
		#body += "\n" + json.dumps(i) + "\n"
		current_datetime = datetime.strptime(i["@timestamp"], datetime_format)
		if (latest_datetime == None):
			latest_datetime = current_datetime
		delta = current_datetime - latest_datetime
		#print("current: ", current_datetime)
		#print("latest: ", latest_datetime)
		#print("delta: ", delta.total_seconds() )
		if(current_datetime > latest_datetime):
			latest_datetime = current_datetime
		time.sleep(delta.total_seconds())
		logslist = [] #the list will only ever have one, but sendlogs wants a list, so we shall oblige
		logslist.append(i)
		response = send_logs(logslist, ip, port, index)
		print('\033[F' + str(num) )
		if(response != "<Response [200]>"):
			error("Bad response log #: " + num)

	print("done.")


def clear_index(index):
	global security, username, password

	notify("clearing index: " + index)

	if(security):
		prot = "https://"
	else:
		prot = "http://"

	es_url = prot + ip + ":" + str(port) + "/" + index + "?pretty"

	headers = {
		'Content-Type': 'application/json',
	}

	response = requests.delete(es_url, headers=headers, data=None, auth=(username, password), verify=False)

	notify(str(response))

	exit(0)


def setup():
	#want to use globals.... oh, python :D
	global verbose, ip, port, time_option, log_file, index, delay, username, password, security
	
	#define arguments / help screen
	parser = argparse.ArgumentParser(description='This program exists to provide functionality required to forward host and network logs from previously executed cyber experiments to an active ELK stack for analysis in conjunction with associated effects.')

	#optional
	parser.add_argument('-c', '--config', type=argparse.FileType('r'), help="Provided .conf file is used to avoid command-line options each run. If not provided, will attempt to use './log_controller.conf'. Command line options override provided configuration file.")
	parser.add_argument('-i', '--ip', help="IP Address for CSOC / ELK stack used in experiment.")
	parser.add_argument('-p', '--port', type=int, help="Port to forward logs to in CSOC / ELK stack used in expirement. Default is 9200 (Elasticsearch).")
	parser.add_argument('-t', '--time', help="Option for updating timestamps of associated logs.\n\tno_update - use timestamps in log file\n\tnow - use current system time\n\ttimetamp - user provided timestamp in format \'Y-m-d H:M:S.f\'")
	parser.add_argument('-v', '--verbose', action='store_true', help="Set this flag for verbose output information.")
	parser.add_argument('-d', '--delay', action='store_true', help="Set this flag to have logs wait to upload. Without, all logs upload at once.")
	parser.add_argument('--clear_index', help="Option to clear provided index name.")
	parser.add_argument('-n', '--index', help="Define an index to upload documents to in ELK stack.")
	parser.add_argument('-f', '--file', type=argparse.FileType('r'), help="Filename of file containing logs to forward.")
	parser.add_argument('--username', help="Username for ELK stack API calls.")
	parser.add_argument('--password', help="Password for ELK stack API calls.")
	parser.add_argument('-s', '--secure', action='store_true', help="Set this flag to force HTTPS. Note that this tool will ignore certificate errors.")



	#do parse
	args = vars(parser.parse_args())

	#set verbosity
	if(args['verbose']):
		verbose=True

	#check if delay set
	if(args['delay']):
		delay=True

	#check if need SSL
	if(args['secure']):
		security=True

	#if -c parse config
	if(args['config']):
		notify("Reading provided config file . . .")
		config = configparser.ConfigParser()
		config.read(args['config'].name)
		if (not 'ELK' in config) or not ('ip' in config['ELK'] and 'port' in config['ELK'] and 'time' in config ['ELK']):
			error("Bad config provided. See README for example. Attempting to use command line options . . .")
			return -1
		ip=config['ELK']['ip']
		port=config['ELK']['port']
		time_option=config['ELK']['time']
		if 'index' in config['ELK']:
			index=config['ELK']['index']
		if 'username' in config['ELK']:
			username=config['ELK']['username']
		if 'password' in config['ELK']:
			password=config['ELK']['password']


	#override conf options with command line if present
	if(args['ip']):
		ip=args['ip']
	if(args['port']):
		port=args['port']
	if(args['time']):
		time_option=args['time']
	if(args['index']):
		index=args['index']
	if(args['username']):
		username=args['username']
	if(args['password']):
		password=args['password']
	
	#last check for all options
	if not ip:
		error("IP not set.")
		return -1
	if not port:
		port = 9200
	if not time_option: 
		error("No time option Provided.")
		return -1
	if not index:
		error("No index provided.")
		return -1
	if username == '':
		error("No username provided.")
		return -1
	if password == '':
		error("No password provided.")
		return -1
	
	notify("Running with options:\n\tIP: "+ip+":"+str(port)+"\n\tTimestamps: "+time_option+"\n\tIndex: "+index+"\n\tAuthentication: "+username+":"+password)

	#check for clear index command
	if not args['clear_index'] == None:
		clear_index(args['clear_index'])	

	#grab log dump to upload
	if args['file'] == None:
		error("Provide log file!")
		return -1
	log_file = args['file'].name

	return 0


if __name__=="__main__":
	if setup():
		exit(1)
	logs = parse_logs(log_file)
	logs = update_timestamps(logs, time_option)
	if delay:
		trickle_logs(logs, ip, port, index)
	else:
		response = send_logs(logs, ip, port, index)
	notify(response)
	exit(0)
