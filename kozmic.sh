#!/bin/bash
set -e

sudo su <<EOF
/usr/bin/mysqld_safe &
sleep 5
mysql -e 'create database rsstank_test character set utf8 collate utf8_general_ci;'

pip install -r ./requirements/basic.txt
pip install -r ./requirements/dev.txt
EOF

cp ./rsstank/config_local.py-travis ./rsstank/config_local.py
./test.sh
