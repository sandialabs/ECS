#!/bin/bash

# just runs the parsers and sorts the jsons

PATH=$PATH:~/ECS_DEV_TUI/toolkit/

mkdir suricata zeek

cd zeek

zeek LogAscii::use_json=T -r ../*.pcap

bro_parser.sh < ~/target_ips.txt >> ALL_ZEEK.json

cd ..
cd suricata

suricata -r ../*.pcap
preprocess_suricata.sh eve.json | jq -c >> processed_suricata.json
grep -vE "10\.5\.7\." processed_suricata.json >> trimmed_suricata.json

cd ..
cp zeek/ALL_ZEEK.json ./ ; cp suricata/trimmed_suricata.json ./Suricata.json


