#!/usr/bin/env python
# coding: utf-8
import functools

from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

import rsstank
from rsstank.poll_feeds import main as poll_feeds
from rsstank.send_feeds import main as send_feeds
from rsstank.update_feeds import main as update_feeds
from rsstank.cleanup import main as cleanup


def sentrify(f):
    """Декоратор, логирующий все исключения функции в Sentry (
    :obj:`rsstank.sentry`.
    """
    if not rsstank.sentry:
        return f

    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except:
            rsstank.sentry.captureException()
            raise

    return decorated_function


# Присваиваем функциям осмысленные имена (изначально они все
# называются "main") для того, чтобы Flask-Script знал,
# как называть команды ./manage.py
poll_feeds.__name__ = 'poll_feeds'
send_feeds.__name__ = 'send_feeds'
update_feeds.__name__ = 'update_feeds'
cleanup.__name__ = 'cleanup'


manager = Manager(rsstank.app)
manager.add_command('db', MigrateCommand)

for command in (poll_feeds, send_feeds, update_feeds, cleanup):
    manager.command(sentrify(command))


if __name__ == '__main__':
    manager.run()
