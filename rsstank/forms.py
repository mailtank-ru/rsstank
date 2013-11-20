# coding: utf-8
import flask.ext.wtf as wtf


class AuthForm(wtf.Form):
    """Форма аутентификации по ключу"""
    mailtank_key = wtf.TextField(u'Ключ проекта Mailtank', [wtf.validators.Required()])


class KeyForm(wtf.Form):
    """Форма редактирования настроек для ключа"""
    is_enabled = wtf.BooleanField(u'Включен', [wtf.validators.NumberRange(0, 1)])
    namespace = wtf.TextField(u'Пространство имен (маска для тэгов)')
