#!/usr/bin/env bash

websrc="https://charachorder.io/firmware"

get_name_from_json () {
	json="$1"
	echo "$json" | awk '{print $2}' | awk -F':' '{print $2}' | sed 's/"//g' | \
		sed 's/,//'
}

get_device_list() {
	devices_json=$(curl -X 'GET' \
		"${websrc}/" \
		-H 'accept: application/json')
	echo "$devices_json"
}


get_firmware_list() {
	device="$1"
	curl -X 'GET' "${websrc}/${device}/" -H 'accept: application/json'
}

get_firmware_list() {
	device="$1"
	curl -X 'GET' "${websrc}/${device}/" -H 'accept: application/json'
}

get_metadata() {
	device="$1"
	firmware="$2"
	dataset_name="actions.json"
	dataset_name="$3"
	curl -X 'GET' \
		"${websrc}/${device}/${firmware}/${dataset_name}" \
		-H 'accept: */*'
}

#device_names=$(get_name_from_json "$(get_device_list)")
#device=$(echo "$device_names" | fzf)
#firmware_names=$(get_name_from_json "$(get_firmware_list $device)")
#firmware=$(echo "$firmware_names" | fzf)
device="m4g_s3"
firmware="3.0.0-gamma.1"
echo "$device $firmware"
action_names="$(get_metadata $device $firmware 'actions.json')"
echo "$action_names"
#firmware_ver=$(get_name_from_json "$(get_firmware_list $device)")
