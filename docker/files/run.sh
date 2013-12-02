#!/bin/bash

cd /home/rsstank/

config=$(<./config_local.py-docker);
config="$config\n    SENTRY_DSN = '$SENTRY_DSN'"
config="$config\n    SECRET_KEY = '$SECRET_KEY'"
config="$config\n    SQLALCHEMY_DATABASE_URI = '$SQLALCHEMY_DATABASE_URI'"
echo -e "$config" > ./src/rsstank/config_local.py

cd ./src

RSSTANK_CONFIG=rsstank.config_local.ProductionConfig ./manage.py db upgrade head

supervisord -n
