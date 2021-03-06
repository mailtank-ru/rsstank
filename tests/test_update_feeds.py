# coding: utf-8
import json

import mock
import httpretty
import furl

from . import TestCase
from rsstank import update_feeds, db
from rsstank.update_feeds import sync
from rsstank.models import AccessKey, Feed


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

    def test_sync(self):
        # Проверям добавление тега
        tags = ['rss:a:http://go-go-go.rss/feed:100']
        key = AccessKey(content='asdf', namespace='a')

        sync(tags, key)

        feed = Feed.query.first()
        assert feed.url == 'http://go-go-go.rss/feed'

        # Проверяем теги с разными интервалами
        tags = ['rss:a:http://go-go-go.rss/feed:100',
                'rss:a:http://go-go-go.rss/feed:200']

        sync(tags, key)
        assert 2 == Feed.query.count()

        # Проверяем удаление тега
        tags = ['rss:a:http://go-go-go.rss/feed:200']

        sync(tags, key)
        feed = Feed.query.first()
        assert feed.sending_interval == 200

        # Проверяем теги с разными адресами
        tags = ['rss:a:http://no-no-no.rss/feed:200',
                'rss:a:http://go-go-go.rss/feed:200']
        sync(tags, key)
        assert 2 == Feed.query.count()
        assert Feed.query.filter_by(url='http://no-no-no.rss/feed').first()

        # Проверяем обработку плохого тега
        tags = ['rss:a:http://go-go-go.rss/feed:asdf']
        sync(tags, key)
        assert not Feed.query.first()

        tags = ['rss:a:aisudhfoiasuh']
        sync(tags, key)
        assert not Feed.query.first()
        
        # Проверяем случай, когда тег содержит юникодовый URL
        tags = [u'rss:a:http://go-go-go.rss/feed?arg=привет!:200']
        sync(tags, key)
        assert not Feed.query.first()

    @httpretty.httprettified
    def test_main(self):
        def request_callback(method, uri, headers):
            if 'rss:b:' == furl.furl(uri).args['mask']:
                return (403, headers, '')
            if 'rss:d:' == furl.furl(uri).args['mask']:
                return (500, headers, '')
            return (200, headers, json.dumps(TAGS_DATA))

        httpretty.register_uri(
            httpretty.GET,
            '{}/tags/'.format(self.app.config['MAILTANK_API_URL']),
            body=request_callback)

        a_key = AccessKey(namespace='a', content='one', is_enabled=True)
        b_key = AccessKey(namespace='b', content='two', is_enabled=True)
        c_key = AccessKey(namespace='c', content='disabled', is_enabled=False)
        d_key = AccessKey(namespace='d', content='errored', is_enabled=True)
        db.session.add_all([a_key, b_key, c_key])
        db.session.commit()

        with mock.patch('rsstank.update_feeds.sync', autospec=True) as sync_mock:
            update_feeds.main()

            db.session.refresh(a_key)
            db.session.refresh(b_key)

            # Синхронизация проведена только для хорошего ключа
            sync_mock.assert_called_once_with(mock.ANY, a_key)

            args, kwargs = sync_mock.call_args
            tags, key = args
            expected_tags = set([tag['name'] for tag in TAGS_DATA['objects']])
            assert set(tags) == expected_tags

            # Ключ, на запрос с которым Mailtank ответил 403, выключился
            assert not b_key.is_enabled
            # Клюс, на который Mailtank ответил 500, остался включенным
            assert d_key.is_enabled
