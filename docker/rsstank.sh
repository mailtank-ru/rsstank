#!/bin/bash
mkdir -p ./logs
docker run -e SECRET_KEY='secret' \
           -e SENTRY_DSN='' \
           -e SQLALCHEMY_DATABASE_URI='mysql://user:@192.168.33.10/rsstank' \
           -v $PWD/logs:/logs -p 8080:8080 -t $1 /home/rsstank/run.sh
