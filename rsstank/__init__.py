# coding: utf-8
import os

import flask
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.migrate import Migrate


app = flask.Flask(__name__)
config = os.environ.get('RSSTANK_CONFIG', 'rsstank.config.DefaultConfig')
app.config.from_object(config)


db = SQLAlchemy(app)
migrate = Migrate(app)


# Регистрируем вьюхи после инициализации приложения:
from . import views
