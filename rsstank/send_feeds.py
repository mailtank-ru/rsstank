# coding: utf-8
import datetime as dt
import logging

import mailtank
from .models import db, AccessKey, Feed, FeedItem


logger = logging.getLogger(__name__)


def send_feed(feed):
    """Создаёт рассылку, содержащую новые элементы из фида `feed`."""
    items_to_send = feed.items.order_by(FeedItem.pub_date)

    if feed.last_sent_at:
        items_to_send = items_to_send.filter(
            FeedItem.created_at >= feed.last_sent_at)

    items_dict = {}
    for item in items_to_send:
        existed_item = items_dict.get(item.guid, None)
        if not existed_item or item.pub_date > existed_item.pub_date:
            # Элемент фида с таким guid встречается первый раз, либо он более
            # свежий, чем уже встречавшийся
            items_dict[item.guid] = item

    context_items = [item.to_context_entry() for item in items_dict.values()]
    assert context_items  # Потому что никто (никто!) не смеет посылать
                          # пустую рассылку
    try:
        feed.access_key.mailtank.create_mailing(
            target={'tags': [feed.tag]},
            context={'items': context_items})
    except mailtank.MailtankError as e:
        logger.warn('Could not create mailing for %r. Mailtank API has '
                    'returned an error: %r.', feed, e)
    else:
        feed.last_sent_at = dt.datetime.utcnow()


def main():
    """Создаёт рассылки по всем фидам, относящимся ко включенным ключам."""
    for feed in Feed.query.join(AccessKey).filter(AccessKey.is_enabled == True):
        if feed.is_it_time_to_send() and feed.are_there_items_to_send():
            send_feed(feed)
            db.session.add(feed)
            db.session.commit()
