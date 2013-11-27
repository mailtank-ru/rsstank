# coding: utf-8
import datetime as dt

from rsstank.models import Feed, FeedItem


def create_feed(feed_url, key):
    """Конструирует валидный :class:`Feed`."""
    feed = Feed(access_key=key, sending_interval=60 * 60 * 24, url=feed_url)
    feed.tag = 'rss:test:{}:{}'.format(feed.url, feed.sending_interval)
    return feed


def create_feed_item(seed):
    """Конструирует валидный :class:`FeedItem`.

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
