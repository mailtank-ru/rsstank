#!/bin/bash
docker run -e SECRET_KEY='secret' \
           -e SQLALCHEMY_DATABASE_URI='mysql://user:@192.168.33.10/rsstank' \
           -p 8081:8080 -t $1 /home/rsstank/run.sh
