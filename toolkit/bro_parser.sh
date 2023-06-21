#!/bin/bash

# Enter keywords (IP addresses, MAC addresses, domain names, file names, etc.) below, newline separated, ctrl+D or ENTER on empty line when done:


TMP=$(mktemp)

ALL_UIDS=()

while IFS= read -r LINE && [[ -n "$LINE" ]]; do
	UIDS=$(cat ./*.log | grep "$LINE" | jq '.uid')
	for CURR in $UIDS; do
		if [[ -n "$CURR" ]] && [[ "$CURR" != "null" ]] && [[ ! "${ALL_UIDS[*]}" =~ "${CURR}" ]]; then
			#echo $CURR
			ALL_UIDS+=("$CURR")
		fi
	done
done

for CURR in "${ALL_UIDS[@]}"; do
	cat ./*.log | grep "$CURR" >> $TMP
done

cat $TMP | jq -s 'sort_by(.ts)' | jq -c '.[]'

rm $TMP
