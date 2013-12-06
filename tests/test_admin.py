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
        with self.client.session_transaction() as sess:
            sess['key'] = key

    @httpretty.httprettified
    def test_auth(self):
        """Клиент может зайти по ключу Mailtank. Если ключа не было, он создается"""
        httpretty.register_uri(
            httpretty.GET, '{}/tags/'.format(self.app.config['MAILTANK_API_URL']),
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
        form = r.forms['key-form']
        form['namespace'] = 'mask'
        r = form.submit()

        a = AccessKey.query.first()
        assert a.content == 'the_key'
        assert not a.is_enabled
        assert a.namespace == 'mask'

        # Изменяем состояние на "Включен"
        form['is_enabled'] = True
        r = form.submit()
        assert (u'необходимо заполнить это поле' in 
                r.context['form'].layout_id.errors[0])
        
        assert not a.is_enabled
        
        # Изменяем состояние на "Включен"
        form['is_enabled'] = True
        # И при этом указываем идентификатор шаблона
        form['layout_id'] = '84sad823'
        form.submit().follow()

        a = AccessKey.query.first()
        assert a.is_enabled
        assert a.content == 'the_key'
        assert a.namespace == 'mask'

    def test_time_conversion_functions(self):
        utctime = dt.time(hour=2)
        assert utctime_to_localstring(utctime, 'Asia/Yekaterinburg') == 8
        assert utctime_from_localstring(8, 'Asia/Yekaterinburg') == utctime

        utctime = dt.time(hour=22)
        assert utctime_to_localstring(utctime, 'Europe/Moscow') == 2
        assert utctime_from_localstring(2, 'Europe/Moscow') == utctime

    def test_edit_first_send_time(self):
        """Клиент может менять временной промежуток для первой рассылки"""
        self.login('the_key')
        r = self.client.get(self.key_url)

        # Пользователь может установить часовой пояс и сохранить его
        form = r.forms['key-form']

        form['timezone'] = 'UTC'
        r = form.submit()

        key = AccessKey.query.first()
        assert key.timezone == 'UTC'

        form['timezone'] = 'Europe/Moscow'
        r = form.submit().follow()

        key = AccessKey.query.first()
        assert key.timezone == 'Europe/Moscow'

        # Пользователь может изменить начало и конец периода
        form = r.forms['key-form']
        form['local_first_send_interval_start'] = 6
        form['local_first_send_interval_end'] = 14
        r = form.submit()

        key = AccessKey.query.first()
        assert key.first_send_interval_start == dt.time(hour=2)
        assert key.first_send_interval_end == dt.time(hour=10)
    
    @httpretty.httprettified
    def test_create_layout(self):
        """Кнопка "Создать шаблон" работает."""
        httpretty.register_uri(
            httpretty.POST, '{}/layouts/'.format(self.app.config['MAILTANK_API_URL']),
            body=json.dumps({'id': 'qwerty'}))

        self.login('the_key')
        r = self.client.get(self.key_url)

        key = AccessKey.query.first()
        assert not key.layout_id
        
        r = r.forms['layout-form'].submit()
        
        key = AccessKey.query.first()
        assert key.layout_id == 'qwerty'
