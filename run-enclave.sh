#!/bin/bash

image_eif="$1"
debug="$2"

if [ $image_eif == "" ]
then
	echo >&2 "Usage: $0 IMAGE_EIF"
	exit 1
fi

echo "image_eif: $image_eif"

if [ "$debug" = "--debug" ]
then
echo "🚀 Starting enclave in debug mode."
nitro-cli run-enclave \
	--cpu-count 2 \
	--memory 3000 \
	--enclave-cid 4 \
	--eif-path "$image_eif" \
	--debug-mode \
	--attach-console 
else
echo "🚀 Starting enclave in production mode."
nitro-cli run-enclave \
	--cpu-count 2 \
	--memory 3000 \
	--enclave-cid 4 \
	--eif-path "$image_eif" 
fi