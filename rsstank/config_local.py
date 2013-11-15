# coding: utf-8
from .config import TestingConfig, DefaultConfig


class TestingConfig(TestingConfig):
    SQLALCHEMY_DATABASE_URI = 'mysql://admin:@192.168.33.101/rsstank_test'


class ProductionConfig(DefaultConfig):
    pass
