import datetime

from . import db


class MailtankAccessKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    content = db.Column(db.String, nullable=False, unique=True)
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)
    namespace = db.Column(db.String, nullable=False)


class Feed(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    access_key_id = db.Column(db.Integer, db.ForeignKey('access_key.id'),
                              nullable=False)
    url = db.Column(db.String(2000), nullable=False)
    sending_interval = db.Column(db.Integer, nullable=False)
    last_polled_at = db.Column(db.Datetime)
    last_sent_at = db.Column(db.Datetime)


class FeedItemEnclosure(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    feed_item_id = db.Column(db.Integer, db.ForeignKey('feed_item.id'),
                             nullable=False)
    length = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(500), nullable=False)
    url = db.Column(db.String(2000), nullable=False)


class FeedItemSource(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    feed_item_id = db.Column(db.Integer, db.ForeignKey('feed_item.id'),
                             nullable=False)
    url = db.Column(db.String(2000), nullable=False)
    content = db.Column(db.Text, nullable=False)


class FeedItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    polled_at = db.Column(db.Datetime, nullable=False,
                          default=datetime.datetime.utcnow)
    # Required.  Defines the title of the item
    title = db.Column(db.String(2000), nullable=False)
    # Required. Defines the hyperlink to the item
    link = db.Column(db.String(2000), nullable=False)
    # Required. Describes the item
    description = db.Column(db.Text, nullable=False)
    # Optional. Specifies the e-mail address to the author of the item
    author = db.Column(db.String(1000))
    # Optional. Defines one or more categories the item belongs to
    category = db.Column(db.String(1000))
    # Optional. Allows an item to link to comments about that item
    comments = db.Column(db.String(2000))
    # Optional. Allows a media file to be included with the item
    enclosure_id = db.Column(db.Integer, db.ForeignKey('feed_item_enclosure.id'))
    # Optional. Defines a unique identifier for the item
    guid = db.Column(db.String(1000))
    # Optional. Defines the last-publication date for the item
    pub_date = db.Column(db.Datetime)
    # Optional. Specifies a third-party source for the item
    source_id = db.Column(db.Integer, db.ForeignKey('feed_item_source.id'))
