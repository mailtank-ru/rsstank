# coding: utf-8
import json
import datetime as dt

from flask import url_for
import httpretty

from . import TestCase
from rsstank import db
from rsstank.models import AccessKey
from rsstank.forms import utctime_from_localstring, utctime_to_localstring

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
        self.key_url = url_for('key')
        self.access_key = AccessKey(content='the_key', namespace='space')
        db.session.add(self.access_key)
        db.session.commit()

    def login(self, key):
        with self.app.test_client() as client:
            for cookie in self.client.cookiejar:
                client.cookie_jar.set_cookie(cookie)

            with client.session_transaction() as sess:
                sess['key'] = key

            for cookie in client.cookie_jar:
                cookie.name = str(cookie.name)
                cookie.value = str(cookie.value)
                cookie.domain = self.app.config['SERVER_NAME']
                self.client.cookiejar.set_cookie(cookie)

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
        assert a.content == 'asdf'
        assert not a.is_enabled
        assert a.namespace == ''

    def test_edit(self):
        """Клиент может изменять свойства ключа"""
        self.login('the_key')
        r = self.client.get(self.key_url)

        # Изменяем маску (пространство имен)
        form = r.form
        form['namespace'] = 'mask'
        r = form.submit()

        a = AccessKey.query.first()
        assert a.content == 'the_key'
        assert not a.is_enabled
        assert a.namespace == 'mask'

        # Изменяем состояние на "Включен"
        form['is_enabled'] = 1
        r = form.submit()

        a = AccessKey.query.first()
        assert a.content == 'the_key'
        assert a.is_enabled
        assert a.namespace == 'mask'

    def test_time_conversion_functions(self):
        utctime = dt.time(hour=2)
        assert utctime_to_localstring(utctime, 'Asia/Yekaterinburg') == 8
        assert utctime_from_localstring('8', 'Asia/Yekaterinburg') == utctime

        utctime = dt.time(hour=22)
        assert utctime_to_localstring(utctime, 'Europe/Moscow') == 2
        assert utctime_from_localstring('2', 'Europe/Moscow') == utctime

    def test_edit_first_send_time(self):
        """Клиент может менять временной промежуток для первой рассылки"""
        self.login('the_key')
        r = self.client.get(self.key_url)

        # Пользователь может установить часовой пояс и сохранить его
        form = r.form

        form['timezone'] = 'UTC'
        r = form.submit()

        key = AccessKey.query.first()
        assert key.timezone == 'UTC'

        form['timezone'] = 'Europe/Moscow'
        r = form.submit()

        key = AccessKey.query.first()
        assert key.timezone == 'Europe/Moscow'

        # Пользователь может изменить начало и конец периода
        form = r.form
        form['local_first_send_interval_start'] = 6
        form['local_first_send_interval_end'] = 14
        r = form.submit()

        key = AccessKey.query.first()
        assert key.first_send_interval_start == dt.time(hour=2)
        assert key.first_send_interval_end == dt.time(hour=10)
