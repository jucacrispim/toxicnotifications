# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You shoud have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable-all

from mongomotor import connect
from toxiccore.conf import Settings

__version__ = '0.10.2'

ENVVAR = 'TOXICNOTIFICATIONS_SETTINGS'
DEFAULT_SETTINGS = 'toxicnotifications.conf'

dbconn = None
settings = None
pyrocommand = None


def create_settings_and_connect():
    global settings, dbconn

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
    dbsettings = settings.DATABASE
    dbconn = connect(**dbsettings)


from .base import Notification  # noqa
# The order of the imports here is the order the notifications will be
# displayed in the ui.
from .slack import SlackNotification  # noqa
from .mail import EmailNotification  # noqa
from .custom_webhook import CustomWebhookNotification  # noqa
