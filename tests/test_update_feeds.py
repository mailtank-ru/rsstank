# coding: utf-8
from . import TestCase
from rsstank.update_feeds import sync
from rsstank.models import AccessKey, Feed
from mailtank import Tag


class TestUpdateFeeds(TestCase):
    """Тесты внутренностей ./manage update_feeds"""

    def setup_method(self, method):
        TestCase.setup_method(self, method)

    def test_sync(self):
        tags = [Tag({'name': 'rss:a:100:http://go-go-go.rss/feed'})]
        key = AccessKey(content='asdf', namespace='a')

        sync(tags, key)

        feed = Feed.query.first()
        assert feed.url == 'http://go-go-go.rss/feed'
