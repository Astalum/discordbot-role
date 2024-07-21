#!/bin/bash

ENV_FILE_PATH=/path/to/.env

if [[ -e ${ENV_FILE_PATH} ]]; then
	. ${ENV_FILE_PATH}
fi

# Start the Docker container
Docker run --name attender -it python:3.11.9 /bin/bash
