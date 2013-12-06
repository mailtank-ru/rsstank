# coding: utf-8
import datetime as dt

import pytz
import wtforms
from flask.ext import wtf


class RequiredIf(wtforms.validators.Required):
    def __init__(self, other_field_name, *args, **kwargs):
        self.other_field_name = other_field_name
        super(RequiredIf, self).__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('No field named "%s" in the form.'.format(
                self.other_field_name))
        if other_field.data:
            super(RequiredIf, self).__call__(form, field)


class AuthForm(wtf.Form):
    """Форма аутентификации по ключу"""
    mailtank_key = wtforms.TextField(u'Ключ проекта Mailtank', [wtforms.validators.Required()])


def utctime_from_localstring(hour, tz):
    """Преобразует `hour` с часовым поясом `tz` в :class:`datetime.time`
    с часовым поясом UTC.

    :type hour: int
    :type tz: str
    """
    t = dt.time(hour=hour)
    dtime = dt.datetime.combine(dt.date.today(), t)
    local_dtime = pytz.timezone(tz).localize(dtime)
    utc_dt = local_dtime.astimezone(pytz.UTC)
    return utc_dt.time()


def utctime_to_localstring(t, tz):
    """Преобразует `t` в часы, используя часовой пояс из `tz`.

    :type t: :class:`datetime.time`
    :type tz: str
    :rtype: int
    """
    dtime = dt.datetime.combine(dt.date.today(), t).replace(tzinfo=pytz.UTC)
    local_dt = dtime.astimezone(pytz.timezone(tz))
    return local_dt.hour


class KeyForm(wtf.Form):
    """Форма редактирования настроек для ключа"""
    is_enabled = wtforms.BooleanField(u'Включен',
                                      [wtforms.validators.NumberRange(0, 1)])
    namespace = wtforms.TextField(u'Пространство имен (маска для тегов)',
                                  [wtforms.validators.Required()])
    layout_id = wtforms.TextField(u'Идентификатор шаблона',
                                  [RequiredIf('is_enabled', message=
                                      u'Чтобы активировать ключ, необходимо '
                                      u'заполнить это поле.')])
    timezone = wtforms.SelectField(u'Часовой пояс',
                                   choices=[(tz, tz) for tz in pytz.common_timezones])
    local_first_send_interval_start = \
        wtforms.SelectField(u'Начало временного промежутка первой рассылки',
                            choices=[(i, '{}:00'.format(i)) for i in range(0, 24)],
                            coerce=int)
    local_first_send_interval_end = \
        wtforms.SelectField(u'Конец временного промежутка первой рассылки',
                            choices=[(i, '{}:00'.format(i)) for i in range(0, 24)],
                            coerce=int)

    def validate_timezone(form, field):
        try:
            pytz.timezone(field.data)
        except pytz.UnknownTimeZoneError:
            field.errors.append(u'Неправильный часовой пояс')
            return False
        return True

    def populate_obj(self, key):
        super(KeyForm, self).populate_obj(key)
        key.first_send_interval_start = utctime_from_localstring(
            self.local_first_send_interval_start.data,
            self.timezone.data)
        key.first_send_interval_end = utctime_from_localstring(
            self.local_first_send_interval_end.data,
            self.timezone.data)
