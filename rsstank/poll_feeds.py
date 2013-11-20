# coding: utf-8
import time
import datetime
import collections
import concurrent.futures

import requests
import feedparser
import reppy.parser
import sqlalchemy
from furl import furl

from .models import db, Feed, FeedItem


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
    response = requests.get(robots_txt_url)
    rules = reppy.parser.Rules(
        robots_txt_url, response.status_code, response.content,
        time.time() + 3600)  # Последний параметр -- это TLL, в течение которого
                             # будет валиден robots.txt. Нас функционал
                             # перезапрашивания robots.txt не волнует, поэтому
                             # передаём туда первое попавшееся валидное значение.
    return rules[agent]


def poll_feed(feed):
    """Сохраняет элементы фида в БД."""
    response = requests.get(feed.url)
    feed_data = feedparser.parse(response.content)

    for entry in feed_data.entries:
        feed_item = FeedItem.from_feedparser_entry(entry)
        feed_item.feed_id = feed.id

        db.session.begin(nested=True)
        db.session.add(feed_item)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            db.session.rollback()

    feed.last_polled_at = datetime.datetime.utcnow()


def poll_feeds(rules, feed_ids):
    """Сохраняет элементы фидов в БД.

    :param feed_ids: список идентификаторов фидов. URL-ы этих фидов должны
                     иметь один и тот же хост, правила доступа к которому
                     задаются аргументом `rules`
    :type rules: :class:`reppy.parser.Agent`
    """
    def _process(feed_id):
        feed = Feed.query.get(feed_id)
        if rules.allowed(feed.url):
            poll_feed(feed)
            db.session.commit()
        else:
            pass  # TODO Логировать?
    
    # Хотим спать _только между_ вызовами `poll_feed` (т.е., не хотим спать
    # после последнего вызова) -- отсюда такая схема с откусыванием головы.
    feed_ids = iter(feed_ids)
    feed_id = feed_ids.next()
    _process(feed_id)
    for feed_id in feed_ids:
        # Уважаем Crawl-delay и спим, дабы соблюсти указанную задержку
        time.sleep(rules.delay)
        a = time.time()
        _process(feed_id)


def get_feed_ids_by_hosts():
    rv = collections.defaultdict(list)
    for feed in Feed.query.all():
        host = furl(feed.url).host
        rv[host].append(feed.id)
    return rv


def main():
    """Обновляет содержимое фидов."""
    feed_ids_by_hosts = get_feed_ids_by_hosts()
    
    host_rules = {}
    for host in feed_ids_by_hosts.keys():
        host_rules[host] = get_robots_rules(host, 'rsstank/0.1')

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_host = {}
        for host, feed_ids in feed_ids_by_hosts.iteritems():
            future = executor.submit(poll_feeds, host_rules[host], feed_ids)
            future_to_host[future] = host

        for future in concurrent.futures.as_completed(future_to_host):
            host = future_to_host[future]
            if future.exception() is not None:
                exc = future.exception()
                print host, exc
