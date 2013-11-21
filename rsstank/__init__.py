# coding: utf-8
import os
import logging

import flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.migrate import Migrate
from raven.contrib.flask import Sentry
from raven.handlers.logging import SentryHandler


app = flask.Flask(__name__)
config = os.environ.get('RSSTANK_CONFIG', 'rsstank.config.DefaultConfig')
app.config.from_object(config)

db = SQLAlchemy(app)
migrate = Migrate(app)


formatter = logging.Formatter('%(asctime)s: %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

logger = logging.getLogger(__package__)
loglevel = getattr(logging, app.config.get('RSSTANK_LOGLEVEL', 'INFO'))
logger.setLevel(loglevel)
logger.addHandler(console_handler)


sentry = None
if app.config['SENTRY_DSN'] and not app.config['TESTING']:
    sentry = Sentry(app)
    sentry_handler = SentryHandler(app.config['SENTRY_DSN'])
    sentry_handler.setLevel(logging.WARNING)
    logger.addHandler(sentry_handler)


# Регистрируем вьюхи после инициализации приложения:
from . import views
