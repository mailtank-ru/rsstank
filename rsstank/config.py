# coding: utf-8
class DefaultConfig(object):
    DEBUG = False
    TESTING = False

    SENTRY_DSN = None
    SQLALCHEMY_DATABASE_URI = None
    RSSTANK_LOGLEVEL = 'INFO'
    RSSTANK_AGENT = 'rsstank/0.1'


class DevelopmentConfig(DefaultConfig):
    DEBUG = True
    SECRET_KEY = 'development'
    SQLALCHEMY_DATABASE_URI = 'mysql://root:@localhost/rsstank'


class TestingConfig(DefaultConfig):
    TESTING = True
    SECRET_KEY = 'testing'
    SQLALCHEMY_DATABASE_URI = 'mysql://root:@localhost/rsstank_test'
    SERVER_NAME = 'rsstank.local'
    MAILTANK_API_URL = 'http://api.mailtank.local'
    RSSTANK_LOGLEVEL = 'WARNING'
