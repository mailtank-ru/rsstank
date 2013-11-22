# coding: utf-8
import json

import mock
import httpretty
import furl

from . import TestCase
from rsstank import update_feeds, db
from rsstank.update_feeds import sync
from rsstank.models import AccessKey, Feed
from mailtank import Tag

TAGS_DATA = {
    'objects': [
        {'name': 'rss:a:http://go.rss/feed:100'},
        {'name': u'rss:a:http://фид.рф:200'},
        {'name': u'rss:a:http://another.namespace:200'},
        {'name': u'rss:a:www.bad.feed:1h'},
    ],
    'page': 1,
    'pages_total': 1,
}

class TestUpdateFeeds(TestCase):
    """Тесты внутренностей ./manage update_feeds"""

    def setup_method(self, method):
        TestCase.setup_method(self, method)

    def test_sync(self):
        # Проверям добавление тэга
        tags = [Tag({'name': 'rss:a:http://go-go-go.rss/feed:100'})]
        key = AccessKey(content='asdf', namespace='a')

        sync(tags, key)

        feed = Feed.query.first()
        assert feed.url == 'http://go-go-go.rss/feed'

        # Проверяем тэги с разными интервалами
        tags = [Tag({'name': 'rss:a:http://go-go-go.rss/feed:100'}),
                Tag({'name': 'rss:a:http://go-go-go.rss/feed:200'})]

        sync(tags, key)
        assert 2 == Feed.query.count()

        # Проверяем удаление тэга
        tags = [Tag({'name': 'rss:a:http://go-go-go.rss/feed:200'})]

        sync(tags, key)
        feed = Feed.query.first()
        assert feed.sending_interval == 200

        # Проверяем тэги с разными адресами
        tags = [Tag({'name': 'rss:a:http://no-no-no.rss/feed:200'}),
                Tag({'name': 'rss:a:http://go-go-go.rss/feed:200'})]
        sync(tags, key)
        assert 2 == Feed.query.count()
        assert Feed.query.filter_by(url='http://no-no-no.rss/feed').first()

        # Проверяем обработку плохого тэга
        tags = [Tag({'name': 'rss:a:http://go-go-go.rss/feed:asdf'})]
        sync(tags, key)
        assert not Feed.query.first()

        tags = [Tag({'name': 'rss:a:aisudhfoiasuh'})]
        sync(tags, key)
        assert not Feed.query.first()

    @httpretty.httprettified
    def test_main(self):
        def request_callback(method, uri, headers):
            if 'rss:b:' == furl.furl(uri).args['mask']:
                return (403, headers, '')
            return (200, headers, json.dumps(TAGS_DATA))

        httpretty.register_uri(
            httpretty.GET,
            '{}/tags'.format(self.app.config['MAILTANK_API_URL']),
            body=request_callback)

        a_key = AccessKey(namespace='a', content='one', is_enabled=True)
        b_key = AccessKey(namespace='b', content='two', is_enabled=True)
        c_key = AccessKey(namespace='b', content='disabled', is_enabled=False)
        db.session.add_all([a_key, b_key, c_key])
        db.session.commit()

        def side_effect(tags, key):
            # Проверяем, что sync была вызвана с нужными тэгами
            call_tags = set([tag.name for tag in tags])
            assert_tags = set([tag['name'] for tag in TAGS_DATA['objects']])
            assert call_tags == assert_tags

        with mock.patch('rsstank.update_feeds.sync', side_effect=side_effect) as sync:
            update_feeds.main()

            db.session.refresh(a_key)
            db.session.refresh(b_key)

            # Синхронизация проведена только для хорошего ключа
            sync.assert_called_once_with(mock.ANY, a_key)

            # Ключ, на запрос с которым Mailtank ответил 403, выключился
            assert b_key.is_enabled is False
            
