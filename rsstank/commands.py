# coding: utf-8
from .models import Feed
from .poll_feeds import main as poll_feeds
from .update_feeds import main as update_feeds


def sync_feed_lists():
    """Синхронизирует список фидов каждого из ключей доступа."""
    print 'sync_feed_lists'


def send_feeds():
    """Создаёт рассылки с новым содержимым фидов."""
    print 'send_feeds'
