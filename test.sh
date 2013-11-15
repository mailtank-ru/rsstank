#!/bin/sh
if [[ -z $RSSTANK_CONFIG ]]; then
    RSSTANK_CONFIG=rsstank.config_local.TestingConfig 
fi

PYTHONPATH=".:$PYTHONPATH" RSSTANK_CONFIG=$RSSTANK_CONFIG \
    py.test -s --tb=short --cov rsstank --cov-report term-missing $@
