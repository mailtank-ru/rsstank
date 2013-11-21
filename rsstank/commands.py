# coding: utf-8
from .models import Feed
from .poll_feeds import main as poll_feeds
from .send_feeds import main as send_feeds


def sync_feed_lists():
    """Синхронизирует список фидов каждого из ключей доступа."""
    print 'sync_feed_lists'
