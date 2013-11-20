# coding: utf-8
import datetime

from . import db


class AccessKey(db.Model):
    """Ключ доступа к API Mailtank."""

    id = db.Column(db.Integer, primary_key=True)

    #: Содержимое ключа доступа
    content = db.Column(db.String(255), nullable=False, unique=True)
    #: Включен ли функционал rsstank для данного ключа?
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)
    #: Пространство имён ключа (используется для ограничения множества
    #: тегов, с которыми работает rsstank)
    namespace = db.Column(db.String(255), nullable=False)


class Feed(db.Model):
    """Фид."""

    id = db.Column(db.Integer, primary_key=True)
    access_key_id = db.Column(db.Integer, db.ForeignKey('access_key.id'),
                              nullable=False)
    #: URL RSS-фида
    url = db.Column(db.String(2000), nullable=False)
    #: Интервал в секундах, с которым генерируются рассылки
    #: с новыми элементами фида
    sending_interval = db.Column(db.Integer, nullable=False)
    #: Дата и время последнего обновления элементов фида
    last_polled_at = db.Column(db.DateTime)
    #: Дата и время последнего создания рассылки по фиду
    last_sent_at = db.Column(db.DateTime)
    #: Ключ доступа к Mailtank API, к которому привязан фид
    access_key = db.relationship(
        'AccessKey',
        backref=db.backref('feeds', lazy='dynamic', cascade='all'))

    def __repr__(self):
        return '<Feed #{0} {1}>'.format(self.id, self.url[:60])


class FeedItem(db.Model):
    """Элемент фида."""

    __table_args__ = (
        # `guid` может быть очень большим, в то время как MySQL
        # ограничивает длину проиндексированного поля 767 байтами.
        # Указывая `mysql_length`, мы говорим MySQL строить
        # индекс не по всему полю, а только по первым его 255 символам.
        # 255 умножить на три (MySQL использует только три байта
        # для хранения UTF-8 символов) меньше 767.
        db.Index('unique_guid_within_a_feed', 'feed_id', 'guid',
                 unique=True, mysql_length={'guid': 255}),
    )

    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=datetime.datetime.utcnow)

    feed = db.relationship(
        'Feed', backref=db.backref('items', lazy='dynamic', cascade='all'))

    # XXX TODO Нижеследующие поля отражают стандарт RSS.
    # Вероятно, стоит сделать набор полее более общим, так, чтобы
    # он стал подходящим для хранения элементов и Atom-фидов.

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

    # Optional. Defines a unique identifier for the item
    guid = db.Column(db.String(2000))
    # Optional. Defines the last-publication date for the item
    pub_date = db.Column(db.DateTime)

    # Optional. Allows a media file to be included with the item
    enclosure_length = db.Column(db.Integer)
    enclosure_type = db.Column(db.String(500))
    enclosure_url = db.Column(db.String(2000))

    # Optional. Specifies a third-party source for the item
    source_url = db.Column(db.String(2000))
    source_content = db.Column(db.String(2000))

    @staticmethod
    def from_feedparser_entry(entry):
        """Конструирует :class:`FeedItem` из :class:`feedparser.FeedParserDict`."""
        feed_item = FeedItem(
            title=entry['title'],
            link=entry['link'],
            description=entry['description'],
            pub_date=entry.get('published_parsed'),
            author=entry.get('author'),
            comments=entry.get('comments'),
            guid=entry.get('guid'))
        enclosures = entry.get('enclosures')
        if enclosures:
            enclosure = enclosures[0]
            feed_item.enclosure_url = enclosure.get('href')
            feed_item.enclosure_length = enclosure.get('length')
            feed_item.enclosure_type = enclosure.get('type')
        source = entry.get('source')
        if source:
            feed_item.source_url = source.get('href')
            feed_item.source_content = source.get('title')
        tags = entry.get('tags')
        if tags:
            feed_item.category = tags[0].get('label')
        return feed_item
