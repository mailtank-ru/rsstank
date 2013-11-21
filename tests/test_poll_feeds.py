# coding: utf-8
import datetime as dt
import collections

import mock
import httpretty
import feedparser
from furl import furl

from . import TestCase
from rsstank import poll_feeds
from rsstank.models import db, AccessKey, Feed, FeedItem


ROBOTS_TXT_1 = """
User-agent: *
Crawl-delay: 2
"""

ROBOTS_TXT_2 = """
User-agent: *
Crawl-delay: 3

User-agent: rsstank
Disallow: /a/b/*/
Crawl-delay: 1
"""


class TestPollFeeds(TestCase):
    """Тесты внутренностей ./manage.py poll_feeds."""

    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.access_key = AccessKey(content='123', is_enabled=True, namespace='test')
        db.session.add(self.access_key)
        db.session.commit()

    @httpretty.httprettified
    def test_get_robot_rules(self):
        httpretty.register_uri(
            httpretty.GET, 'http://66.ru/robots.txt', body=ROBOTS_TXT_1)

        rules = poll_feeds.get_robots_rules('66.ru', 'Chrome')
        assert rules.delay == 2
        assert rules.allowed('/hello/')

        httpretty.reset()
        httpretty.register_uri(
            httpretty.GET, 'http://66.ru/robots.txt', body=ROBOTS_TXT_2)

        rules = poll_feeds.get_robots_rules('66.ru', 'Chrome')
        assert rules.delay == 3
        assert rules.allowed('/a/b/d/')

        rules = poll_feeds.get_robots_rules('66.ru', 'rsstank/1.0;_20_subscribers')
        assert rules.delay == 1
        assert rules.allowed('/a/c/')
        assert not rules.allowed('/a/b/c/')

    def test_get_feed_ids_by_hosts(self):
        for feed_url in ('http://66.ru/news/society/rss/',
                         'http://66.ru/news/business/rss/',
                         'http://66.ru/news/freetime/rss/',
                         'http://news.yandex.ru/hardware.rss',
                         'http://news.yandex.ru/fire.rss'):
            feed = Feed(access_key=self.access_key,
                        sending_interval=60 * 60 * 24,
                        url=feed_url)
            db.session.add(feed)

        # Добавим выключенный ключ
        disabled_access_key = AccessKey(content='456', is_enabled=False, namespace='test')
        db.session.add(disabled_access_key)
        # И несколько фидов в него, которые мы не хотим видеть
        # в результате работы `get_feed_ids_by_hosts`
        for feed_url in ('http://66.ru/news/politic/rss/',
                         'http://lenta.ru/rss/articles/russia'):
            feed = Feed(access_key=disabled_access_key,
                        sending_interval=60 * 60 * 24,
                        url=feed_url)
            db.session.add(feed)
        db.session.commit()

        feed_ids_by_hosts = poll_feeds.get_feed_ids_by_hosts()

        def get_feeds(host):
            return [feed.id for feed in Feed.query.filter(
                Feed.url.contains('http://{}'.format(host))
            ) if feed.access_key.is_enabled]
        assert set(feed_ids_by_hosts['66.ru']) == \
            set(get_feeds('66.ru'))
        assert set(feed_ids_by_hosts['news.yandex.ru']) == \
            set(get_feeds('news.yandex.ru'))

    @httpretty.httprettified
    def test_poll_feed_basics(self):
        for feed_url in ('http://66.ru/news/society/rss/',
                         'http://news.yandex.ru/hardware.rss'):
            feed = Feed(access_key=self.access_key,
                        sending_interval=60 * 60 * 24,
                        url=feed_url)
            db.session.add(feed)
        db.session.commit()

        with open('./tests/fixtures/66.ru-society-rss') as fh:
            httpretty.register_uri(
                httpretty.GET, 'http://66.ru/news/society/rss/', body=fh.read())
        with open('./tests/fixtures/news.yandex.ru-hardware-rss') as fh:
            httpretty.register_uri(
                httpretty.GET, 'http://news.yandex.ru/hardware.rss', body=fh.read())

        for feed in self.access_key.feeds:
            poll_feeds.poll_feed(feed)

        feed_66_ru = self.access_key.feeds.filter(Feed.url.contains('66.ru')).first()
        assert feed_66_ru.items.count() == 10
        item = feed_66_ru.items.filter_by(guid='66.ru:news:147137').first()
        assert item.description == u'Президент РЖД хочет заменить их двухэтажными.'

        feed_yandex_ru = self.access_key.feeds.filter(Feed.url.contains('yandex.ru')).first()
        assert feed_yandex_ru.items.count() == 15

    @httpretty.httprettified
    def test_poll_feed_ignores_already_seen_items(self):
        feed = Feed(access_key=self.access_key,
                    sending_interval=60 * 60 * 24,
                    url='http://news.yandex.ru/hardware.rss')
        db.session.add(feed)
        db.session.commit()

        # news.yandex.ru-world-rss-1 содержит элементы A B C D E
        with open('./tests/fixtures/news.yandex.ru-world-rss-1') as fh:
            rss_data = fh.read()
            guids_before_update = \
                set(entry['guid'] for entry in feedparser.parse(rss_data).entries)
            httpretty.register_uri(httpretty.GET, feed.url, body=rss_data)

        poll_feeds.poll_feed(feed)
        assert feed.items.count() == 5

        httpretty.reset()
        # news.yandex.ru-world-rss-2 содержит элементы D E F G H
        with open('./tests/fixtures/news.yandex.ru-world-rss-2') as fh:
            rss_data = fh.read()
            guids_after_update = \
                set(entry['guid'] for entry in feedparser.parse(rss_data).entries)
            httpretty.register_uri(httpretty.GET, feed.url, body=rss_data)

        poll_feeds.poll_feed(feed)
        assert feed.items.count() == 8  # 5 штук (A B C D E) + 3 штуки (F G H)

        guids_in_db = [item.guid for item in feed.items]
        # Убедимся, что все guid-ы в БД -- уникальные
        assert len(guids_in_db) == len(set(guids_in_db))
        # И отражают записи как до "обновления фида", так и после
        assert set(guids_in_db) == (guids_before_update | guids_after_update)

    @httpretty.httprettified
    def test_main(self):
        httpretty.register_uri(
            httpretty.GET, 'http://news.yandex.ru/robots.txt', body=ROBOTS_TXT_1)
        httpretty.register_uri(
            httpretty.GET, 'http://66.ru/robots.txt', body=ROBOTS_TXT_2)

        for feed_url in ('http://66.ru/news/society/rss/',
                         'http://66.ru/news/business/rss/',
                         'http://66.ru/news/freetime/rss/',
                         'http://news.yandex.ru/hardware.rss',
                         'http://news.yandex.ru/fire.rss'):
            feed = Feed(access_key=self.access_key,
                        sending_interval=60 * 60 * 24,
                        url=feed_url)
            db.session.add(feed)
        db.session.commit()

        call_datetimes_by_hosts = collections.defaultdict(list)

        def side_effect(feed):
            host = furl(feed.url).host
            call_datetimes_by_hosts[host].append(dt.datetime.utcnow())

        with mock.patch('rsstank.poll_feeds.poll_feed',
                        side_effect=side_effect) as poll_feed_mock:
            poll_feeds.main()

        def assert_deltas_equal(sequence, x, precision):
            deltas = [next_el - el for el, next_el in zip(sequence, sequence[1:])]
            assert all(x < delta < x + precision for delta in deltas)

        call_datetimes = call_datetimes_by_hosts['66.ru']
        assert len(call_datetimes) == 3
        assert_deltas_equal(
            call_datetimes,
            dt.timedelta(seconds=1),
            dt.timedelta(milliseconds=15))

        call_datetimes = call_datetimes_by_hosts['news.yandex.ru']
        assert len(call_datetimes) == 2
        assert_deltas_equal(
            call_datetimes,
            dt.timedelta(seconds=2),
            dt.timedelta(milliseconds=15))
