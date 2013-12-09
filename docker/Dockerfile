FROM ubuntu:12.04
RUN echo "deb http://archive.ubuntu.com/ubuntu precise main universe" > /etc/apt/sources.list
RUN apt-get -y update
# Install postfix to make cron happy and not discard stdout:
RUN apt-get -y install cron unzip wget python-dev python-pip supervisor libmysqlclient-dev postfix rsyslog
RUN pip install distribute==0.6.34
RUN pip install uwsgi
RUN useradd -m -d /home/rsstank -s /usr/sbin/nologin rsstank
RUN wget --no-check-certificate https://github.com/mailtank-ru/rsstank/archive/master.zip -O /tmp/rsstank.zip
RUN unzip /tmp/rsstank.zip -d /tmp/
RUN mv /tmp/rsstank-master /home/rsstank/src/
RUN pip install --use-mirrors -r /home/rsstank/src/requirements/basic.txt

# List ADD directives as late as possible because everything after ADD won't be cached
ADD ./files/config_local.py-docker /home/rsstank/config_local.py-docker
ADD ./files/run.sh /home/rsstank/run.sh
ADD ./files/supervisor.conf /etc/supervisor/conf.d/common.conf
ADD ./files/uwsgi-supervisor.conf /etc/supervisor/conf.d/uwsgi.conf
ADD ./files/cron-supervisor.conf /etc/supervisor/conf.d/cron.conf
ADD ./files/rsyslog-supervisor.conf /etc/supervisor/conf.d/rsyslog.conf
ADD ./files/uwsgi.ini /home/rsstank/uwsgi.ini
ADD ./files/crontab /etc/crontab
ADD ./files/cron-rsyslog.conf /etc/rsyslog.d/60-cron.conf
RUN chown root:root /etc/supervisor/conf.d/* /home/rsstank/uwsgi.ini /etc/crontab /etc/rsyslog.d/60-cron.conf
RUN chmod +x /home/rsstank/run.sh
