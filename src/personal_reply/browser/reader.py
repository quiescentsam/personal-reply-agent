from __future__ import annotations

from personal_reply.browser.connector import connect_to_chrome
from personal_reply.browser.whatsapp import read_whatsapp_thread
from personal_reply.browser.models import ThreadContext
from personal_reply.config import Config


def read_active_whatsapp_thread(config: Config) -> ThreadContext:
    with connect_to_chrome(debug_url=config.chrome_debug_url) as page:
        return read_whatsapp_thread(page, sender_names=config.sender_names)
