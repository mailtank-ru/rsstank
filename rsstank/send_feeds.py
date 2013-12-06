# coding: utf-8
import datetime as dt
import logging

import mailtank
from .models import db, AccessKey, Feed, FeedItem


logger = logging.getLogger(__name__)


def send_feed(feed):
    """Создаёт рассылку, содержащую новые элементы из фида `feed`."""
    items_to_send = feed.items.order_by(FeedItem.pub_date.desc())

    if feed.last_sent_at:
        items_to_send = items_to_send.filter(
            FeedItem.created_at >= feed.last_sent_at)

    unique_items = []
    for item in items_to_send:
        if not item.guid in [item_u.guid for item_u in unique_items]:
            unique_items.append(item)

    context_items = [item.to_context_entry() for item in reversed(unique_items)]
    assert context_items  # Потому что никто (никто!) не смеет посылать
                          # пустую рассылку
    try:
        feed.access_key.mailtank.create_mailing(
            layout_id=feed.access_key.layout_id,
            target={
                'tags': [feed.tag],
                'unsubscribe_tags': [feed.tag],
            },
            context={'items': context_items})
    except mailtank.MailtankError as e:
        logger.warn('Could not create mailing for %r. Mailtank API has '
                    'returned an error: %r.', feed, e)
    else:
        feed.last_sent_at = dt.datetime.utcnow()
        logger.info('%i items have been sent from %r.', len(unique_items), feed)


def main():
    """Создаёт рассылки по всем фидам, относящимся ко включенным ключам."""
    logger.info('send_feeds has started.')

    for feed in Feed.query.join(AccessKey).filter_by(is_enabled=True):
        if feed.is_it_time_to_send() and feed.are_there_items_to_send():
            send_feed(feed)
            db.session.add(feed)
            db.session.commit()

    logger.info('send_feeds has finished.')
