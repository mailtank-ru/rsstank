# coding: utf-8
import datetime as dt
import logging

import mailtank
from .models import db, AccessKey, Feed, FeedItem


logger = logging.getLogger(__name__)


def send_feed(feed):
    items_to_send = feed.items.order_by(FeedItem.pub_date)
    if feed.last_sent_at:
        items_to_send = items_to_send.filter(
            FeedItem.created_at >= feed.last_sent_at)
    context = {
        'items': [item.to_context_entry() for item in items_to_send],
    }
    try:
        feed.access_key.mailtank.create_mailing(
            target={'tags': [feed.tag]},
            context=context)
    except mailtank.MailtankError:
        # TODO
    else:
        feed.last_sent_at = dt.datetime.utcnow()


def main():
    for feed in Feed.query.join(AccessKey).filter(AccessKey.is_enabled == True):
        if feed.is_it_time_to_send() and feed.are_there_items_to_send():
            send_feed(feed)
            db.session.add(feed)
            db.session.commit()

