# coding: utf-8
import logging

from .models import db, AccessKey, Feed
from mailtank import MailtankError

logger = logging.getLogger(__name__)


def sync(tags, key):
    """Синхронизирует фиды ключа key Rsstank в соответствии с тэгами Mailtank"""
    feeds = key.feeds.all()
    feeds_by_url = {feed.url: feed for feed in feeds}

    for tag in tags:
        rss, namespace, interval, url = tag.name.split(':', 3)
        feed = feeds_by_url.get(url, Feed(access_key=key))
        feed.namespace, feed.sending_interval, feed.url = namespace, interval, url
        db.session.add(feed)

    for feed in feeds:
        db.session.delete(feed)

    db.session.commit()


def main():
    """Обновляет фиды в соответствии с тэгами rss в Mailtank"""
    logger.info('update_feeds has started.')

    keys = AccessKey.query.filter_by(is_enabled=True)

    for key in keys:
        mask = u'rss:{}:'.format(key.namespace)
        try:
            tags = key.mailtank.get_tags(mask=mask)
        except MailtankError as e:
            # Что-то пошло не так, помечаем ключ как 'выключенный'
            logger.info(u'Error during connecting with key {0}: "{1}"'
                        .format(key.content, e))
            key.is_enabled = False
        else:
            logger.info(u'Tags for key {} have been successfully fetched'
                        .format(key.content))
            sync(tags, key)
