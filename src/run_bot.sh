#!/bin/bash 

#TELEGRAM BOT API TOKEN 
TOKEN="${1}" 

if [ -z ${TOKEN} ]; then 
    echo "Please provide your telegram bot API token as first argument. Abort."
    exit 1 
fi 

#RESULTING DOCKER IMAGE 
IMAGE_NAME="recipesbot" 

TEST_FOLDER="${PWD}/test"
DB_PATHNAME="${TEST_FOLDER}/new_db"

#build image
docker build -t ${IMAGE_NAME} . 

#run container from built image 
docker run --rm -v ${DB_PATHNAME}:/data ${IMAGE_NAME} \
    --token ${TOKEN} \
    --data /data/your_recipes.db