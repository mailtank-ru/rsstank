#!/usr/bin/env python
# coding: utf-8
from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand

import rsstank.commands


manager = Manager(rsstank.app)
manager.add_command('db', MigrateCommand)
manager.command(rsstank.commands.poll_feeds)
manager.command(rsstank.commands.send_feeds)
manager.command(rsstank.commands.update_feeds)


if __name__ == '__main__':
    manager.run()
