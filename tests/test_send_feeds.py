# coding: utf-8
import datetime as dt

import pytest
import mock
import freezegun
import testfixtures

import mailtank
from rsstank import app, send_feeds
from rsstank.models import db, AccessKey, Feed, FeedItem
from . import TestCase, fixtures


def get_first_send_interval_as_datetimes(utc_now=None):
    utc_start_time, utc_end_time = \
        app.config['RSSTANK_DEFAULT_FIRST_SEND_INTERVAL']
    if not utc_now:
        utc_now = dt.datetime.utcnow()
    utc_today = utc_now.date()
    utc_interval_start = dt.datetime.combine(utc_today, utc_start_time)
    utc_interval_end = dt.datetime.combine(utc_today, utc_end_time)
    return utc_interval_start, utc_interval_end


class TestSendFeeds(TestCase):
    """Тесты внутренностей ./manage.py send_feeds."""

    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.access_key = AccessKey(content='123', is_enabled=True,
                                    namespace='test')
        self.disabled_access_key = AccessKey(content='456', is_enabled=False,
                                             namespace='test2')
        db.session.add(self.access_key)
        db.session.add(self.disabled_access_key)
        db.session.commit()

    def test_feed_item_to_context_entry(self):
        feed_item = fixtures.create_feed_item(seed=1)

        expected_context_entry = {
            'category': u'Category 1',
            'link': u'http://66.ru/1.rss',
            'description': u'Description 1',
            'title': u'Title 1',
            'author': u'Author 1',
            'guid': u'1',
            'pub_date': '2013-11-20 12:00:00',
            'comments': u'http://66.ru/comments/1/'
        }
        assert feed_item.to_context_entry() == expected_context_entry

        feed_item.enclosure_url = 'http://66.ru/logo.png'
        feed_item.enclosure_type = 'image/png'
        expected_context_entry['enclosure'] = {
            'url': feed_item.enclosure_url,
            'type': feed_item.enclosure_type,
            'length': None,
        }
        assert feed_item.to_context_entry() == expected_context_entry

        feed_item.source_url = 'http://www.nytimes.com/2013/09/12/opinion/putin.html'
        expected_context_entry['source'] = {
            'url': feed_item.source_url,
            'content': None,
        }
        assert feed_item.to_context_entry() == expected_context_entry

    def test_feed_is_it_time_to_send_1(self):
        """Тестирует `Feed.is_it_time_to_send` ни разу не посланного фида."""
        feed = fixtures.create_feed('http://example.com/example.rss', self.access_key)
        assert not feed.last_sent_at

        utc_interval_start, utc_interval_end = get_first_send_interval_as_datetimes()
        # Середина сегодняшнего интервала, в который можно впервые посылать фиды
        utc_interval_median = \
            utc_interval_start + (utc_interval_end - utc_interval_start) / 2

        with freezegun.freeze_time(utc_interval_median):
            assert feed.is_it_time_to_send()

        with freezegun.freeze_time(utc_interval_end + dt.timedelta(hours=1)):
            assert not feed.is_it_time_to_send()

    def test_feed_is_it_time_to_send_2(self):
        """Тестирует `Feed.is_it_time_to_send` фида, посланного ранее."""
        feed = fixtures.create_feed('http://example.com/example.rss', self.access_key)
        feed.last_sent_at = dt.datetime.utcnow().replace(microsecond=0)
        feed.sending_interval = 60 * 60 * 24

        with freezegun.freeze_time(feed.last_sent_at + dt.timedelta(hours=23)):
            assert not feed.is_it_time_to_send()

        with freezegun.freeze_time(feed.last_sent_at + dt.timedelta(hours=23, seconds=59)):
            assert not feed.is_it_time_to_send()

        with freezegun.freeze_time(feed.last_sent_at + dt.timedelta(hours=24)):
            assert feed.is_it_time_to_send()

    def test_feed_are_there_items_to_send(self):
        feed = fixtures.create_feed('http://example.com/example.rss', self.access_key)
        feed.access_key = self.access_key
        feed.last_sent_at = dt.datetime.utcnow() - dt.timedelta(days=3)
        db.session.add(feed)

        assert not feed.are_there_items_to_send()

        for i in range(10):
            feed_item = fixtures.create_feed_item(i)
            feed_item.created_at = dt.datetime.utcnow() - dt.timedelta(days=i)
            feed.items.append(feed_item)
        db.session.commit()

        assert feed.are_there_items_to_send()

        feed.last_sent_at = dt.datetime.utcnow() + dt.timedelta(days=1)
        assert not feed.are_there_items_to_send()

    def test_send_feed_boundary_cases(self):
        feed = fixtures.create_feed('http://example.com/example-1.rss', self.access_key)
        feed.access_key = self.access_key
        db.session.add(feed)
        db.session.commit()

        # Притворяемся глупыми и зовёт send_feed с фидом, у которого нет
        # новых элементов. Ожидаем споткнуться о проверку:
        with pytest.raises(AssertionError):
            send_feeds.send_feed(feed)

        # Добавляем в него элементов
        for i in range(1, 3):
            feed_item = fixtures.create_feed_item(i)
            feed_item.created_at = dt.datetime.utcnow() + dt.timedelta(days=i)
            feed.items.append(feed_item)
        db.session.commit()

        class MailtankErrorStub(mailtank.MailtankError):
            def __init__(self, code, message):
                self.code = code
                self.message = message

        # Делаем вид, что Mailtank API вернул 503
        mailtank_error_stub = MailtankErrorStub(503, 'Whoops')
        with mock.patch('mailtank.Mailtank.create_mailing',
                        autospec=True, side_effect=mailtank_error_stub):
            with testfixtures.LogCapture() as l:
                send_feeds.send_feed(feed)

        # Проверяем, что происшествие отражено в логах
        log_record = l.records[-1]
        assert log_record.levelname == 'WARNING'
        log_message = log_record.getMessage()
        assert repr(mailtank_error_stub) in log_message
        assert repr(feed) in log_message

    def test_unique_items_in_mailing(self):
        feed = fixtures.create_feed('http://example.com/example-1.rss', self.access_key)
        feed.sending_interval = 60 * 60 * 24
        feed.access_key = self.access_key

        # Создаем два элемента с разными `pub_date` и одинаковыми `guid`
        item1 = fixtures.create_feed_item(1)
        item2 = fixtures.create_feed_item(1)
        item3 = fixtures.create_feed_item(3)

        item2.pub_date = dt.datetime(2013, 11, 21, 12, 00, 00) - dt.timedelta(days=2)
        feed.items.extend([item2, item1, item3])
        db.session.add(feed)
        db.session.commit()

        # Проверяем, что в рассылке не будет дублирующихся элементов фида
        with mock.patch('mailtank.Mailtank.create_mailing',
                        autospec=True) as create_mailing_mock:
            send_feeds.send_feed(feed)

        call, args = create_mailing_mock.call_args
        context = args['context']
        assert len(context['items']) == 2
        assert context['items'][1]['pub_date'] == \
            item1.pub_date.strftime('%Y-%m-%d %H:%M:%S')

    def test_context_contains_channel_data(self):
        feed = fixtures.create_feed('http://example.com/example-1.rss', self.access_key)
        item = fixtures.create_feed_item(1)
        feed.items.append(item)
        db.session.add(feed)
        db.session.commit()

        with mock.patch('mailtank.Mailtank.create_mailing',
                        autospec=True) as create_mailing_mock:
            send_feeds.send_feed(feed)

        call, args = create_mailing_mock.call_args
        context = args['context']
        assert context['channel']['link'] == feed.channel_link
        assert context['channel']['description'] == feed.channel_description
        assert context['channel']['title'] == feed.channel_title
        assert context['channel']['image_url'] == feed.channel_image_url

    def test_main(self):
        # Создаём фид номер раз
        feed_1 = fixtures.create_feed('http://example.com/example-1.rss', self.access_key)
        feed_1.sending_interval = 60 * 60 * 24
        feed_1.access_key = self.access_key
        db.session.add(feed_1)

        # Добавляем в него элементы датированные от "сегодня минус 9 дней" до
        # "вчера"
        for i in range(1, 10):
            feed_item = fixtures.create_feed_item(i)
            feed_item.created_at = dt.datetime.utcnow() - dt.timedelta(days=i)
            feed_1.items.append(feed_item)
        db.session.commit()

        # Создаём фид номер два
        feed_2 = fixtures.create_feed('http://example.com/example-2.rss', self.access_key)
        feed_2.sending_interval = 60 * 60 * 24
        feed_2.access_key = self.access_key
        db.session.add(feed_2)

        # Добавляем в него элементы датированные от "сегодня минус 3 дня" до
        # "вчера"
        for i in range(1, 3):
            feed_item = fixtures.create_feed_item(i)
            feed_item.created_at = dt.datetime.utcnow() - dt.timedelta(days=i)
            feed_2.items.append(feed_item)
        db.session.commit()

        # Случай номер 1
        # ==============
        # Заявляем, что в последний раз посылали первый фид три дня назад
        feed_1.last_sent_at = dt.datetime.utcnow() - dt.timedelta(days=4)

        # Замораживаем время где-нибудь в будущем, но точно вне интервала,
        # допускающего посылку вида впервые
        _, utc_interval_end = get_first_send_interval_as_datetimes(
            utc_now=dt.datetime.utcnow() + dt.timedelta(days=1))
        freezed_utc_now = utc_interval_end + dt.timedelta(seconds=1)
        with freezegun.freeze_time(freezed_utc_now):
            with mock.patch('mailtank.Mailtank.create_mailing',
                            autospec=True) as create_mailing_mock:
                send_feeds.main()

        # Проверяем, что create_mailing позвался однажды
        assert create_mailing_mock.call_count == 1

        # С верным контекстом и целью
        _, kwargs = create_mailing_mock.call_args

        context = kwargs['context']
        assert len(context['items']) == 4

        target = kwargs['target']
        target_tags = target['tags']
        assert len(target_tags) == 1
        assert target_tags[0] == feed_1.tag

        # Проверяем, что вызов команды обновил `last_sent_at` фида
        assert feed_1.last_sent_at == freezed_utc_now

        # Случай номер 2
        # ==============
        # Запускаем команду в это же время во второй раз. Ничего не должно произойти
        with mock.patch('mailtank.Mailtank.create_mailing',
                        autospec=True) as create_mailing_mock:
            with freezegun.freeze_time(freezed_utc_now):
                send_feeds.main()
                assert not create_mailing_mock.called

        # Случай номер 3
        # ==============
        # (*) Добавляем новые элементы в первый фид, датируя их будущим
        for i in range(10, 15):
            feed_item = fixtures.create_feed_item(i)
            feed_item.created_at = feed_1.last_sent_at + dt.timedelta(hours=i)
            feed_1.items.append(feed_item)
        db.session.commit()

        # И посылаем рассылку гарантированно по истечению `sending_interval` первого
        # фида, притом так, чтобы текущее время попало в интервал, допускающий
        # посылку фидов впервые (что должно вызвать посылку второго фида)
        freezed_utc_now = feed_1.last_sent_at + dt.timedelta(
            days=1, seconds=feed_1.sending_interval)
        _, freezed_utc_now = get_first_send_interval_as_datetimes(
            utc_now=freezed_utc_now)

        with freezegun.freeze_time(freezed_utc_now):
            with mock.patch('mailtank.Mailtank.create_mailing',
                            autospec=True) as create_mailing_mock:
                send_feeds.main()

        # Проверяем, что создались _две_ рассылки (для первого фида
        # это вторая рассылка, для второго -- первая)
        assert create_mailing_mock.call_count == 2

        contexts_by_target_tag = {}
        for _, kwargs in create_mailing_mock.call_args_list:
            tag = kwargs['target']['tags'][0]
            context = kwargs['context']
            contexts_by_target_tag[tag] = context

        # На _два_ различных тега
        assert set(contexts_by_target_tag.keys()) == {feed_1.tag, feed_2.tag}
        # Проверяем, что из первого фида послались элементы,
        # добавленные после последней его посылки (см. (*)), ...
        len(contexts_by_target_tag[feed_1.tag]['items']) == 4
        # ...а второй фид послался впервые, захватив все два своих элемента.
        len(contexts_by_target_tag[feed_2.tag]['items']) == 2

        assert feed_1.last_sent_at == freezed_utc_now
        assert feed_2.last_sent_at == freezed_utc_now
