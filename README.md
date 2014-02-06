## Getting started

1. Установить зависимости, перечисленные в `requirements/basic.txt`;
2. Настроить приложение, создав `rsstank.config_local` по образу и подобию
   `rsstank/config_local.py-dist`;

Для запуска dev-сервера:

`RSSTANK_CONFIG=rsstank.config_local.DevelopmentConfig ./manage.py runserver`

Для запуска тестов:

1. Установить зависимости, перечисленные в `requirements/dev.txt`;
2. `./test.sh`

Сборка и запуск приложения в Docker-контейнере:

```
cd docker
docker build .
./rsstank.sh <container-id>
```

## Формат тегов

`rss:<namespace>:<url>:<interval>`, где:

* `<namespace>` — пространство имён, которое указывается в настройках ключа;
* `<url>` — URL RSS- или Atom-фида;
* `<interval>` — интервал в секундах между рассылками фидов.
