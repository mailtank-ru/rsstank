# coding: utf-8
from . import app


@app.route('/')
def index():
    """Вьюшка с формой ввода ключа от Mailtank"""
    return 'It works! :)'


@app.route('/key/')
def key():
    """Вьюшка, позволяющая менять настройки ключа от Mailtank в системе.
    Ожидает в POST параметрах 'key'"""
    return 'Look at this key, dude!'
