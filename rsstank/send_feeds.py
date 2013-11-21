# coding: utf-8
import datetime as dt
import logging

from .models import db, AccessKey, Feed, FeedItem


logger = logging.getLogger(__name__)


def are_there_items_to_send(feed):
    latest_created_at = feed.items.with_entities(
        db.func.max(FeedItem.created_at)
    ).scalar()
    return feed.last_sent_at >= latest_created_at


def is_it_time_to_send(feed):
    return (feed.last_sent_at + dt.timedelta(seconds=feed.sending_interval) <=
            dt.datetime.utcnow())


def send_feed(feed):
    items_to_send = feed.items.filter(
        FeedItem.created_at > feed.last_sent_at
    ).order_by(FeedItem.pub_date).all()
    context = {
        'items': [item.to_context_entry() for item in items_to_send],
    }
    feed.access_key.mailtank.create_mailing(  # TODO
        target={
            'tags': ['tag'],
        },
        context=context)


def main(host, scheme='http'):
    for feed in Feed.query.join(AccessKey).filter(AccessKey.is_enabled == True):
        if is_it_time_to_send(feed) and are_there_items_to_send(feed):
            send_feed(feed)

