# coding: utf-8
import datetime as dt


class DefaultConfig(object):
    DEBUG = False
    TESTING = False

    SENTRY_DSN = None
    SQLALCHEMY_DATABASE_URI = None
    MAILTANK_API_URL = 'http://api.mailtank.ru'
    RSSTANK_LOGLEVEL = 'INFO'
    RSSTANK_AGENT = 'rsstank/0.1'
    #: Crawl-delay, который будет использоваться в случае, если
    #: хост не задал свои правила в robots.txt
    RSSTANK_DEFAULT_CRAWL_DELAY = 1
    #: UTC-время суток, в которое стоит осуществлять рассылку
    #: свежедобавленных фидов (дефолтное значение это 02:00-04:00,
    #: то есть от 8 до 10 утра по Екатеринбургу).
    RSSTANK_DEFAULT_FIRST_SEND_INTERVAL = (dt.time(hour=2), dt.time(hour=4))


class DevelopmentConfig(DefaultConfig):
    DEBUG = True
    SECRET_KEY = 'development'


class TestingConfig(DefaultConfig):
    TESTING = True
    SECRET_KEY = 'testing'
    SERVER_NAME = 'rsstank.local'
    MAILTANK_API_URL = 'http://api.mailtank.local'
    RSSTANK_LOGLEVEL = 'WARNING'
