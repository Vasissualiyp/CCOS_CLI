#!/usr/bin/env bash

websrc="https://charachorder.io"

devices_json=$(curl -X 'GET' \
  "${websrc}/firmware/" \
  -H 'accept: application/json')

get_name_from_json () {
	json="$1"
	echo "$json" | awk '{print $2}' | awk -F':' '{print $2}' | sed 's/"//g' | \
		sed 's/,//'
}

device_names=$(get_name_from_json "$devices_json")

echo "$device_names" | fzf
