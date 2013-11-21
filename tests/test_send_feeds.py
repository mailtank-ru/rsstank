# coding: utf-8
import datetime as dt
from rsstank import send_feeds
from rsstank.models import db, AccessKey, Feed, FeedItem
from . import TestCase


def create_feed_item(seed):
    """
    :type seed: :class:`int`
    """
    return FeedItem(
        title='Title {}'.format(seed),
        link='http://66.ru/{}.rss'.format(seed),
        description='Description {}'.format(seed),
        pub_date=dt.datetime(2013, 11, 21, 12, 00, 00) - dt.timedelta(days=seed),
        guid=str(seed),
        author='Author {}'.format(seed),
        comments='http://66.ru/comments/{}/'.format(seed),
        category='Category {}'.format(seed))


class TestSendFeeds(TestCase):
    """Тесты внутренностей ./manage.py send_feeds."""

    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.access_key = AccessKey(content='123', is_enabled=True,
                                    namespace='test')
        self.disabled_access_key = AccessKey(content='456', is_enabled=False,
                                             namespace='test2')
        db.session.add(self.access_key)
        db.session.add(self.disabled_access_key)

        for feed_url in ('http://66.ru/news/society/rss/',
                         'http://news.yandex.ru/hardware.rss'):
            feed = Feed(access_key=self.access_key,
                        sending_interval=60 * 60 * 24,
                        url=feed_url)
            db.session.add(feed)

        for feed_url in ('http://66.ru/news/politic/rss/',
                         'http://lenta.ru/rss/articles/russia'):
            feed = Feed(access_key=self.disabled_access_key,
                        sending_interval=60 * 60 * 24,
                        url=feed_url)
            db.session.add(feed)

        #for feed in Feed.query.all():
            #for guid in range(1, 10):
                #db.session.add(create_feed_item(feed, guid))
        #db.session.commit()

    def test_feed_item_to_context_entry(self):
        feed_item = create_feed_item(seed=1)
        expected_context_entry = {
            'category': u'Category 1',
            'link': u'http://66.ru/1.rss',
            'description': u'Description 1',
            'title': u'Title 1',
            'author': u'Author 1',
            'guid': u'1',
            'pub_date': '2013-11-20 12:00:00',
            'comments': u'http://66.ru/comments/1/'
        }
        assert feed_item.to_context_entry() == expected_context_entry

        feed_item.enclosure_url = 'http://66.ru/logo.png'
        feed_item.enclosure_type = 'image/png'
        expected_context_entry['enclosure'] = {
            'url': feed_item.enclosure_url,
            'type': feed_item.enclosure_type,
            'length': None,
        }
        assert feed_item.to_context_entry() == expected_context_entry

        feed_item.source_url = 'http://www.nytimes.com/2013/09/12/opinion/putin.html'
        expected_context_entry['source'] = {
            'url': feed_item.source_url,
            'content': None,
        }
        assert feed_item.to_context_entry() == expected_context_entry
