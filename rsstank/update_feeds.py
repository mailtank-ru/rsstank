# coding: utf-8
import logging

from .models import db, AccessKey, Feed
from mailtank import MailtankError

logger = logging.getLogger(__name__)


def sync(tags, key):
    """Синхронизирует фиды ключа `key` rsstank в соответствии с тегами `tags` Mailtank"""
    feeds = key.feeds.all()
    # Строим словарь из фидов с ключом 'интервал:адрес'
    feeds_by_url = \
        {u'{0}:{1}'.format(feed.sending_interval, feed.url): feed for feed in feeds}

    for tag in tags:
        if ':' not in tag.name:
            continue
        head, rest = tag.name.split(':', 1)
        if head != 'rss':
            continue

        try:
            # Парсим тег
            namespace, url_and_interval = rest.split(':', 1)
            url, interval = url_and_interval.rsplit(':', 1)
            interval = int(interval)
        except ValueError as e:
            # Плохой тег
            logger.warn(u'Error "{0}" during parsing tag: {1}'.format(e, tag.name))
        else:
            # Ищем, есть ли фид для этого тега, если нет то создаем
            feed = feeds_by_url.get(u'{0}:{1}'.format(interval, url))
            if feed:
                feeds.remove(feed)
            else:
                db.session.add(
                    Feed(access_key=key, sending_interval=interval, url=url, tag=tag))
            logger.info(u'Tag {} synced'.format(tag.name))

    for feed in feeds:
        # Удаляем фиды, для которых не было тега
        db.session.delete(feed)

    db.session.commit()


def main():
    """Обновляет фиды в соответствии с тегами проекта в Mailtank."""
    logger.info('update_feeds has started.')

    keys = AccessKey.query.filter_by(is_enabled=True)

    for key in keys:
        mask = u'rss:{}:'.format(key.namespace)
        try:
            tags = key.mailtank.get_tags(mask=mask)
        except MailtankError as e:
            # Что-то пошло не так, помечаем ключ как 'выключенный'
            logger.warn(u'Error during connecting with key {0}: "{1}"'
                        .format(key.content, e))
            key.is_enabled = False
            db.session.add(key)
            db.session.commit()
        else:
            logger.info(u'Tags for key {} have been successfully fetched'
                        .format(key.content))
            sync(tags, key)

    logger.info('update_feeds has finished.')
