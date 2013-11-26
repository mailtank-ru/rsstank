# coding: utf-8
import time
import datetime
import collections
import concurrent.futures
import logging

import requests
import feedparser
import reppy.parser
import sqlalchemy
from furl import furl

from . import app
from .models import db, AccessKey, Feed, FeedItem


logger = logging.getLogger(__name__)


def get_robots_txt_url(host, scheme='http'):
    """Возвращает URL robots.txt для хоста `host`. Схема URL будет
    соответствовать аргументу `scheme`.
    """
    f = furl()
    f.scheme = scheme
    f.host = host
    f.path = 'robots.txt'
    return str(f)


def get_robots_rules(host, agent):
    """Возвращает объект :class:`reppy.parser.Agent`, содержащий
    правила, заданные в robots.txt хоста `host` для юзер-агента `agent`.
    """
    robots_txt_url = get_robots_txt_url(host)
    try:
        response = requests.get(robots_txt_url)
    except requests.exceptions.RequestException:
        return None
    else:
        rules = reppy.parser.Rules(
            robots_txt_url, response.status_code, response.content,
            time.time() + 3600)  # Последний параметр -- это TLL, в течение которого
                                 # будет валиден robots.txt. Нас функционал
                                 # перезапрашивания robots.txt не волнует, поэтому
                                 # передаём туда первое попавшееся валидное значение.
        return rules[agent]


def poll_feed(feed):
    """Сохраняет элементы фида в БД.

    :type feed: :class:`rsstank.models.Feed`
    """
    logger.info('Polling %r.', feed)

    response = requests.get(feed.url)
    feed_data = feedparser.parse(response.content)

    items_saved_n = 0
    for entry in feed_data.entries:
        feed_item = FeedItem.from_feedparser_entry(entry)
        feed_item.feed_id = feed.id

        db.session.begin(nested=True)
        db.session.add(feed_item)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            # IntegrityError может быть вызван тем, что в базе уже существует
            # FeedItem с таким же `feed_id` и `guid`. Это абсолютно нормально;
            # мы должны лишь откатить вложенную транзакцию.
            db.session.rollback()
        else:
            items_saved_n += 1

    feed.last_polled_at = datetime.datetime.utcnow()
    logger.info('%i items have been saved from %r.', items_saved_n, feed)


def poll_feeds(feed_ids, rules=None):
    """Сохраняет элементы фидов с идентификаторами `feed_ids` в БД.

    :param feed_ids: список идентификаторов фидов. URL-ы этих фидов должны
                     указывать на один и тот же хост, правила доступа к
                     которому задаются аргументом `rules`
    :type rules: :class:`reppy.parser.Agent`
    """
    def _process(feed_id):
        feed = Feed.query.get(feed_id)
        if not rules or rules.allowed(feed.url):
            poll_feed(feed)
            db.session.commit()
        else:
            logger.warn('Accessing %r is forbidden by host\'s robots.txt.', feed)

    # Хотим спать _только между_ вызовами `poll_feed` (т.е., не хотим спать
    # после последнего вызова) -- отсюда такая схема с откусыванием головы.
    feed_ids = iter(feed_ids)
    feed_id = feed_ids.next()
    _process(feed_id)
    for feed_id in feed_ids:
        # Уважаем Crawl-delay и спим, дабы соблюсти задержку.
        # Note: `rules.delay` может быть None, если в robots.txt не была
        # указана задержка
        time.sleep((rules and rules.delay) or
                   app.config['RSSTANK_DEFAULT_CRAWL_DELAY'])
        _process(feed_id)


def get_feed_ids_by_hosts():
    """Возвращает словарь, ключами которого являются имена хостов,
    а значениями -- списки идентификаторов фидов, чьи URL указызывают
    на этот хост.

    Перечисляются только фиды, относящиеся ко включенным ключам (`is_enabled`).

    :rtype: {str: [int]}
    """
    rv = collections.defaultdict(list)
    for feed in Feed.query.join(AccessKey).filter(AccessKey.is_enabled == True):
        host = furl(feed.url).host
        rv[host].append(feed.id)
    return rv


def main():
    """Обновляет содержимое всех фидов, относящихся ко включенным ключам."""
    logger.info('poll_feeds has started.')

    # Группируем идентификаторы фидов по хостам
    feed_ids_by_hosts = get_feed_ids_by_hosts()

    # Опрашиваем robots.txt всех хостов
    host_rules = {}
    for host in feed_ids_by_hosts.keys():
        host_rules[host] = get_robots_rules(host, app.config['RSSTANK_AGENT'])

    # Заводим пул из 20 потоков
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_host = {}
        for host, feed_ids in feed_ids_by_hosts.iteritems():
            # Делегируем таск "обнови все фиды хоста" пулу потоков.
            # 1. `poll_feeds` обновляет фиды последовательно, уважая robots.txt
            # 2. Ни для какого хоста `poll_feeds` не будет позван дважды.
            future = executor.submit(poll_feeds, feed_ids, rules=host_rules[host])
            future_to_host[future] = host
            logger.info('%i feeds for host %s has been enqueued for polling.',
                        len(host_rules), host)

        for future in concurrent.futures.as_completed(future_to_host):
            host = future_to_host[future]
            if future.exception() is not None:
                logger.warn('An error has occured during polling %s feeds: "%s".',
                            host, future.exception())
            else:
                logger.info('All feeds from %s have been successfully polled.', host)

    logger.info('poll_feeds has finished.')
