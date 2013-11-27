# coding: utf-8
import logging

from .models import db, Feed, FeedItem


logger = logging.getLogger(__name__)


def delete_sent_feed_items(feed):
    """Удаляет все элементы из фида `feed`, которые были созданы до даты
    последнего отправления фида
    """
    if feed.last_sent_at:
        items_to_delete = feed.items.filter(FeedItem.created_at < feed.last_sent_at).all()
        logger.info('{0} outdated feed items found for feed #{1} with tag {2}'
                    .format(len(items_to_delete), feed.id, feed.tag))
        for item in items_to_delete:
            db.session.delete(item)
        db.session.commit()


def main():
    """Удаляет отправленные элементы всех фидов"""
    logger.info('cleanup has started.')
    for feed in Feed.query.all():
        delete_sent_feed_items(feed)
    logger.info('cleanup has finished.')
