# coding: utf-8
import json
import datetime as dt

from flask import url_for
import httpretty

from . import TestCase
from rsstank import db
from rsstank.models import AccessKey
from rsstank.forms import utctime_from_localstring, utctime_to_localstring, TimeString

TAGS_DATA = {
    'objects': [
        {u'name': 'type_main_news'},
        {'name': 'type_spec'},
        {'name': ''},
        {'name': 'type_unknown'},
        {'name': 'tag_7523'},
        {'name': 'tag_11592'},
        {'name': 'tag_23517'},
        {'name': 'tag_7447'},
        {'name': 'tag_23758'},
        {'name': 'tag_23464'},
    ],
    'page': 1,
    'pages_total': 1,
}


class TestAdmin(TestCase):
    def setup_method(self, method):
        TestCase.setup_method(self, method)
        self.index_url = url_for('index')
        self.access_key = AccessKey(content='the_key', namespace='mask')
        db.session.add(self.access_key)
        db.session.commit()

    @httpretty.httprettified
    def test_auth(self):
        """Клиент может зайти по ключу Mailtank. Если ключа не было, он создается"""
        httpretty.register_uri(
            httpretty.GET, '{}/tags'.format(self.app.config['MAILTANK_API_URL']),
            responses=[
                httpretty.Response(body='', status=403),
                httpretty.Response(body=json.dumps(TAGS_DATA),
                                   status=200,
                                   content_type='text/json')])

        # Первая попытка неудачна
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'asdfg'
        r = r.form.submit()
        assert len(r.context['form'].mailtank_key.errors) == 1

        # Вторая попытка удачна
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'asdf'
        r = r.form.submit().follow()

        # Проверяем, что ключ создался
        a = AccessKey.query.filter_by(content='asdf').first()
        assert (a.content, a.is_enabled, a.namespace) == ('asdf', False, '')

    @httpretty.httprettified
    def test_edit(self):
        """Клиент может изменять свойства ключа"""
        httpretty.register_uri(
            httpretty.GET, '{}/tags'.format(self.app.config['MAILTANK_API_URL']),
            body=json.dumps(TAGS_DATA), status=200, content_type='text/json')

        # Входим в систему по ключу
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'the_key'
        r = r.form.submit().follow()

        # Изменяем маску (пространство имен)
        form = r.form
        form['namespace'] = 'mask'
        r = form.submit()

        a = AccessKey.query.first()
        assert (a.content, a.is_enabled, a.namespace) == ('the_key', False, 'mask')

        # Изменяем состояние на "Включен"

        form['is_enabled'] = 1
        r = form.submit()

        a = AccessKey.query.first()
        assert (a.content, a.is_enabled, a.namespace) == ('the_key', True, 'mask')

    def test_time_conversion_functions(self):
        utctime = dt.time(hour=2)
        assert utctime_to_localstring(utctime, 'Asia/Yekaterinburg') == '08:00:00'
        assert utctime_from_localstring('08:00:00', 'Asia/Yekaterinburg') == utctime

    def test_time_validator(self):
        regex = TimeString().regex
        assert regex.match('12:23:34')
        assert regex.match('23:59:59')
        assert regex.match('03:00:00')
        assert regex.match('00:00:00')
        assert not regex.match('24:23:34')
        assert not regex.match('23:60:34')
        assert not regex.match('21:12:64')
        assert not regex.match('24:2334')
        assert not regex.match('124:23:34')
        assert not regex.match('20:233:34')
        assert not regex.match('20:23:345')

    @httpretty.httprettified
    def test_edit_first_send_time(self):
        """Клиент может менять временной промежуток для первой рассылки"""
        httpretty.register_uri(
            httpretty.GET, '{}/tags'.format(self.app.config['MAILTANK_API_URL']),
            body=json.dumps(TAGS_DATA), status=200, content_type='text/json')

        # Входим в систему по ключу
        r = self.client.get(self.index_url)
        r.form['mailtank_key'] = 'the_key'
        r = r.form.submit().follow()

        # Пользователь может установить часовой пояс и сохранить его
        form = r.form

        form['timezone'] = 'asdfasdf'
        r = form.submit()
        assert len(r.context['form'].timezone.errors) == 1

        form['timezone'] = 'utc'
        r = form.submit()

        key = AccessKey.query.first()
        assert key.timezone == 'utc'

        form['timezone'] = 'Europe/Moscow'
        r = form.submit()

        key = AccessKey.query.first()
        assert key.timezone == 'Europe/Moscow'

        # Пользователь может изменить начало и конец периода
        form = r.form
        form['local_first_send_interval_start'] = '06:00:00'
        form['local_first_send_interval_end'] = '14:00:00'
        r = form.submit()

        key = AccessKey.query.first()
        assert key.first_send_interval_start == dt.time(hour=2)
        assert key.first_send_interval_end == dt.time(hour=10)
