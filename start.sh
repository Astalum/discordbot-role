#!/bin/bash

ENV_FILE_PATH=.env

# if [[ -e ${ENV_FILE_PATH} ]]; then
# 	${ENV_FILE_PATH}
# fi

# Start the Docker container
podman build -t attender_im .
docker run -d --name attender --replace attender_im
