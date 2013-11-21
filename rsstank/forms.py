# coding: utf-8
from flask.ext import wtf
import wtforms


class AuthForm(wtf.Form):
    """Форма аутентификации по ключу"""
    mailtank_key = wtforms.TextField(u'Ключ проекта Mailtank', [wtforms.validators.Required()])


class KeyForm(wtf.Form):
    """Форма редактирования настроек для ключа"""
    is_enabled = wtforms.BooleanField(u'Включен', [wtforms.validators.NumberRange(0, 1)])
    namespace = wtforms.TextField(u'Пространство имен (маска для тэгов)')
