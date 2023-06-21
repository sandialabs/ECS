#!/bin/bash

TMP=$(mktemp)

#change to @timestamp, for elastic
jq 'walk(if type == "object" then with_entries( if .key == "timestamp" then .key = "@timestamp" else . end ) else . end)' $1 >> $TMP

TMP2=$(mktemp)

#remove superfluous material from string
jq '.["@timestamp"] |= (. | split(".")[0] )' $TMP >> $TMP2
rm $TMP

TMP3=$(mktemp)

#change to format ingested by log controller and elastic, and change to Zulu
#ASSUMES YOU ARE CONVERTING FROM A PCAP SET TO MST
jq '.["@timestamp"] |= (. | strptime("%Y-%m-%dT%H:%M:%S") | mktime | . + 25200 | strftime("%Y-%m-%dT%H:%M:%S.000Z"))' $TMP2 >>$TMP3
rm $TMP2

cat $TMP3

rm $TMP3
