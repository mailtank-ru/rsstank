# coding: utf-8
import datetime as dt

import mock

from . import TestCase, fixtures
from rsstank import cleanup, db
from rsstank.models import AccessKey, FeedItem


class TestCleanup(TestCase):
    """Тесты внутренностей ./manage cleanup"""

    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.access_key = AccessKey(content='the_key', namespace='space')

        db.session.add(self.access_key)
        db.session.commit()

    def test_delete_sent_feed_items(self):
        current_dt = dt.datetime(2013, 11, 21, 12, 00, 00)
        past_dt = current_dt - dt.timedelta(hours=2)
        future_dt = current_dt + dt.timedelta(hours=2)

        # Создаем фид и элементы фида
        feed = fixtures.create_feed('http://feed.url', self.access_key)
        feed.last_sent_at = current_dt

        item1 = fixtures.create_feed_item(1)
        item2 = fixtures.create_feed_item(2)
        item3 = fixtures.create_feed_item(3)

        feed.items.append(item1)
        feed.items.append(item2)
        feed.items.append(item3)

        db.session.add(feed)
        db.session.commit()

        # Устанавливаем разные даты для элементов фида
        item1.created_at = future_dt
        item2.created_at = past_dt
        item3.created_at = current_dt

        db.session.add(item2)
        db.session.add(item1)
        db.session.add(item3)
        db.session.commit()

        # Проверяем, что удаляются только устаревшие элементы фида
        cleanup.delete_sent_feed_items(feed)
        assert FeedItem.query.count() == 2

        feed.last_sent_at = current_dt+dt.timedelta(hours=1)

        cleanup.delete_sent_feed_items(feed)
        assert FeedItem.query.count() == 1

    def test_main(self):
        db.session.add(fixtures.create_feed('asdfasd', self.access_key))
        db.session.add(fixtures.create_feed('wert', self.access_key))
        db.session.commit()

        # Проверяем, что процедура чистки вызывается для всех фидов
        with mock.patch('rsstank.cleanup.delete_sent_feed_items') as delete:
            cleanup.main()
            assert delete.call_count == 2
