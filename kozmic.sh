#!/bin/bash
set -e  # Exit if any command returns a non-zero status

sudo su <<EOF
/usr/bin/mysqld_safe &
sleep 5
mysql -e 'create database rsstank_test character set utf8 collate utf8_general_ci;'

pip install --quiet -r ./requirements/basic.txt
pip install --quiet -r ./requirements/dev.txt
EOF

cp ./rsstank/config_local.py-travis ./rsstank/config_local.py
./test.sh

