# -*- coding: utf-8 -*-
# Copyright 2018, 2023, 2024 Juca Crispim <juca@poraodojuca.dev>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from pyrocumulus.auth import AccessToken, Permission
from toxiccore.client import BaseToxicClient
from toxicmaster.repository import Repository
from toxicmaster.slave import Slave
from toxicmaster.users import User
from toxicnotifications.cmds import create_auth_token
from toxicnotifications import Notification
from toxicnotifications import settings
from tests import async_test
from tests.functional import BaseFunctionalTest, DummyMasterHoleClient
from tests.functional.custom_webhook import WebHookMessage


class DummyUIClient(DummyMasterHoleClient):

    async def create_slave(self):
        slave_port = settings.SLAVE_PORT
        r = await super().create_slave(slave_port)
        return r


class DummyNotificationsClient(BaseToxicClient):

    def __init__(self, *args, repo_info=None, **kwargs):
        kwargs['use_ssl'] = False
        kwargs['validate_cert'] = False
        super().__init__(*args, **kwargs)
        self.repo_info = repo_info

    async def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'token': '123'}
        await self.write(data)
        response = await self.get_response()
        return response['body']

    async def enable_notification(self, webhook_url=None):
        action = 'enable-notification'
        webhook_url = webhook_url or 'http://localhost:8123/webhookmessage/'
        body = {'name': 'custom-webhook',
                'repository_id': str(self.repo_info['id']),
                'webhook_url': webhook_url}
        r = await self.request2server(action, body)
        return r

    async def disable_notification(self):
        action = 'disable-notification'
        body = {'name': 'custom-webhook',
                'repository_id': str(self.repo_info['id'])}
        r = await self.request2server(action, body)
        return r

    async def list_notifications(self, repo_id=None):
        action = 'list-notifications'
        body = {'repository_id': repo_id}
        r = await self.request2server(action, body)
        return r

    async def remove_all(self):
        action = 'remove-all'
        body = {'owner': self.owner}
        r = await self.request2server(action, body)
        return r

    async def get_secrets(self):
        action = 'get-secrets'
        body = {'owners': [self.owner]}
        r = await self.request2server(action, body)
        return r


class NotificationTest(BaseFunctionalTest):

    @classmethod
    @async_test
    async def setUpClass(cls):
        super().setUpClass()
        cls.user = User(email='toxic@a.com', is_superuser=True)
        await cls.user.save()
        cls.auth_token = await cls._create_access_token()
        dc = DummyUIClient(cls.user, settings.HOLE_ADDR,
                           settings.HOLE_PORT)

        async with dc:
            await dc.create_slave()

        async with dc:
            cls.repo_info = await dc.create_repo()

        async with dc:
            await dc.wait_build_complete()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        super().tearDownClass()
        await Slave.drop_collection()
        await Repository.drop_collection()
        await User.drop_collection()
        await AccessToken.drop_collection()
        await Permission.drop_collection()

    @async_test
    async def tearDown(self):
        await Notification.drop_collection()
        await WebHookMessage.drop_collection()

    @classmethod
    async def _create_access_token(cls):
        uncrypted_token = await create_auth_token()
        return uncrypted_token

    @async_test
    async def test_add_notification(self):
        dc = DummyNotificationsClient('127.0.0.1', settings.PORT,
                                      repo_info=self.repo_info)
        async with dc:
            r = await dc.enable_notification()

        self.assertEqual(r['custom-webhook'], 'enabled')

    @async_test
    async def test_trigger_notification(self):

        dc = DummyNotificationsClient('127.0.0.1', settings.PORT,
                                      repo_info=self.repo_info)
        async with dc:
            await dc.enable_notification()

        dc = DummyUIClient(self.user, settings.HOLE_ADDR,
                           settings.HOLE_PORT)
        async with dc:
            await dc.start_build()

        async with dc:
            await dc.wait_build_complete()

        timeout = 20
        t = 0
        count = 0
        while t < timeout:
            count = await WebHookMessage.objects.count()
            if count > 0:
                break
            await asyncio.sleep(0.1)
            t += 1

        self.assertGreater(count, 0)

    @async_test
    async def test_remove_notification(self):
        dc = DummyNotificationsClient('127.0.0.1', settings.PORT,
                                      repo_info=self.repo_info)
        async with dc:
            await dc.enable_notification()

        async with dc:
            r = await dc.disable_notification()

        self.assertEqual(r['custom-webhook'], 'disabled')

    @async_test
    async def test_list_notifications(self):
        dc = DummyNotificationsClient('127.0.0.1', settings.PORT,
                                      repo_info=self.repo_info)
        async with dc:
            r = await dc.list_notifications()
        self.assertEqual(len(r['notifications']), 3)

    @async_test
    async def test_list_notifications_for_repo(self):

        dc = DummyNotificationsClient('127.0.0.1', settings.PORT,
                                      repo_info=self.repo_info)
        async with dc:
            await dc.enable_notification()

        async with dc:
            r = await dc.list_notifications(
                repo_id=str(self.repo_info['id']))

        notifications = r['notifications']
        for n in notifications:
            if n['name'] == 'custom-webhook':
                break

        self.assertEqual(n['webhook_url']['value'],
                         'http://localhost:8123/webhookmessage/')
