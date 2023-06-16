# -*- coding: utf-8 -*-

import os
from toxicnotifications import create_settings_and_connect as create_settings
from .. import TEST_DATA_DIR


NOTIFICATIONS_DATA_PATH = TEST_DATA_DIR
os.environ['TOXICNOTIFICATIONS_SETTINGS'] = os.path.join(
    NOTIFICATIONS_DATA_PATH, 'toxicnotifications.conf')


create_settings()


from toxicnotifications import settings  # noqa
