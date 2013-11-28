# coding: utf-8
import datetime as dt

import pytz
import dateutil

from mailtank import Mailtank
from . import db, app


default_interval_start, default_interval_stop = \
    app.config['RSSTANK_DEFAULT_FIRST_SEND_INTERVAL']


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
    #: Часовой пояс для пользователя
    timezone = db.Column(db.String(50), default='utc')
    #: Начало интервала первой рассылки в utc
    first_send_interval_start = db.Column(
        db.Time(), default=default_interval_start)
    #: Окончание интервала первой рассылки в utc
    first_send_interval_end = db.Column(
        db.Time(), default=default_interval_stop)

    @property
    def mailtank(self):
        return Mailtank(app.config['MAILTANK_API_URL'], self.content)


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
    #: Тег, из которого была получена информация о фиде
    tag = db.Column(db.String(2200), nullable=False)
    #: Дата и время последнего обновления элементов фида
    last_polled_at = db.Column(db.DateTime)
    #: Дата и время последнего создания рассылки по фиду
    last_sent_at = db.Column(db.DateTime)
    #: Дата и время последней публикации элемента фида
    last_pub_date = db.Column(db.DateTime)
    #: Ключ доступа к Mailtank API, к которому привязан фид
    access_key = db.relationship(
        'AccessKey',
        backref=db.backref('feeds', lazy='dynamic', cascade='all'))

    def __repr__(self):
        return '<Feed #{0} {1}>'.format(self.id, self.url[:60])

    def is_it_time_to_send(self):
        """Возвращает True, если фид допустимо посылать в текущее время;
        False в противном случае.
        """
        utc_now = dt.datetime.utcnow()
        if not self.last_sent_at:
            # Рассылка ни разу не посылалась
            utc_start_time = self.access_key.first_send_interval_start
            utc_end_time = self.access_key.first_send_interval_end
            # Рассказываем, попадает ли текущее время в интервал, когда допустимо
            # впервые посылать фид
            return utc_start_time <= utc_now.time() <= utc_end_time
        else:
            sending_interval = dt.timedelta(seconds=self.sending_interval)
            return self.last_sent_at + sending_interval <= utc_now

    def are_there_items_to_send(self):
        """Возвращает True, если с момента последней посылки в фиде появились
        новые элементы.
        """
        latest_created_at = self.items.with_entities(
            db.func.max(FeedItem.created_at)
        ).scalar()
        if self.last_sent_at:
            return self.last_sent_at < latest_created_at
        else:
            return bool(latest_created_at)


class FeedItem(db.Model):
    """Элемент фида."""
    id = db.Column(db.Integer, primary_key=True)
    feed_id = db.Column(db.Integer, db.ForeignKey('feed.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, index=True,
                           default=dt.datetime.utcnow)

    feed = db.relationship(
        'Feed', backref=db.backref('items', lazy='dynamic', cascade='all'))

    # XXX TODO Нижеследующие поля отражают стандарт RSS.
    # Стоит сделать набор полее более общим, так, чтобы
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
        pub_date = entry.get('published')
        if pub_date:
            pub_date = dateutil.parser.parse(pub_date)
            if pub_date.tzinfo is not None:
                pub_date = pub_date.astimezone(pytz.utc).replace(tzinfo=None)

        feed_item = FeedItem(
            title=entry['title'],
            link=entry['link'],
            description=entry['description'],
            pub_date=pub_date,
            guid=entry.get('guid'),
            author=entry.get('author'),
            comments=entry.get('comments'))
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

    def to_context_entry(self):
        """Возвращает словарь с данными элемента фида."""
        entry = {
            'title': self.title,
            'link': self.link,
            'description': self.description,
            'pub_date': self.pub_date and self.pub_date.strftime('%Y-%m-%d %H:%M:%S'),
            'guid': self.guid,
            'author': self.author,
            'comments': self.comments,
            'category': self.category,
        }

        enclosure = {
            'url': self.enclosure_url,
            'length': self.enclosure_length,
            'type': self.enclosure_type,
        }
        if any(enclosure.itervalues()):
            entry['enclosure'] = enclosure

        source = {
            'url': self.source_url,
            'content': self.source_content,
        }
        if any(source.values()):
            entry['source'] = source

        return entry
