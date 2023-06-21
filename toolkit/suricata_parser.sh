#!/bin/bash

# Enter keywords (IP addresses, MAC addresses, domain names, file names, etc.) below, newline separated, ctrl+D or ENTER on empty line when done:

while IFS= read -r LINE && [[ -n "$LINE" ]]; do
	GREP="$LINE""\\|""$GREP"
done

GREP=${GREP::-2}

cat $1 | grep "$GREP" | jq -s 'sort_by(."@timestamp")' | jq -c '.[]'
#cat $1
