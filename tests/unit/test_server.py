# -*- coding: utf-8 -*-

# Copyright 2018, 2023 Juca Crispim <juca@poraodojuca.dev>

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

import logging
from unittest import TestCase
from unittest.mock import patch, AsyncMock, Mock

from bson import ObjectId
from toxiccommon.exchange import JsonAckMessage
from toxicnotifications import server
from toxicnotifications import (Notification, SlackNotification)
from tests import async_test


class OutputMessageHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        self.server = server.OutputMessageHandler()
        self.obj_id = ObjectId()
        self.notification = SlackNotification(webhook_url='https://bla.nada',
                                              repository_id=self.obj_id)
        await self.notification.save()

    @patch('aioamqp.protocol.logger')
    @async_test
    async def tearDown(self, *args, **kwargs):
        await Notification.drop_collection()

    @patch.object(Notification, 'run', AsyncMock(
        spec=Notification.run))
    @async_test
    async def test_run_notifications(self):
        msg = {'repository_id': self.obj_id,
               'event_type': 'buildset-finished'}
        await self.server.run_notifications(msg)
        self.assertTrue(Notification.run.called)

    @patch.object(Notification, 'run', AsyncMock(
        spec=Notification.run))
    @async_test
    async def test_run_notifications_no_notifs(self):
        msg = {'repository_id': self.obj_id,
               'event_type': 'buildset-finished'}
        await Notification.objects.all().delete()
        await self.server.run_notifications(msg)
        self.assertFalse(Notification.run.called)

    @patch.object(server.OutputMessageHandler, 'EXCHANGE', AsyncMock(
        spec=server.notifications))
    @patch.object(server.OutputMessageHandler, 'run_notifications',
                  AsyncMock(
                      spec=server.OutputMessageHandler.run_notifications))
    @async_test
    async def test_handle_notifications_timeout(self):
        msg = AsyncMock(spec=JsonAckMessage)
        msg.body = {'event_type': 'repo-added',
                    'repository_id': self.obj_id}
        consumer = server.OutputMessageHandler\
                         .EXCHANGE.consume.return_value\
                                          .__aenter__.return_value

        async def fm(cancel_on_timeout):
            self.server._stop_consuming_messages = True
            raise server.ConsumerTimeout

        consumer.fetch_message = fm

        await self.server._handle_notifications()
        self.assertFalse(self.server.run_notifications.called)

    @patch.object(server.OutputMessageHandler, 'EXCHANGE', AsyncMock(
        spec=server.notifications))
    @patch.object(server.OutputMessageHandler, 'run_notifications',
                  AsyncMock(
                      spec=server.OutputMessageHandler.run_notifications))
    @async_test
    async def test_handle_notifications(self):
        msg = AsyncMock(spec=JsonAckMessage)
        msg.body = {'event_type': 'build-added',
                    'repository_id': self.obj_id}

        consumer = server.OutputMessageHandler\
                         .EXCHANGE.consume.return_value\
                                          .__aenter__.return_value

        async def fm(cancel_on_timeout):
            self.server._stop_consuming_messages = True
            return msg

        consumer.fetch_message = fm

        await self.server._handle_notifications()
        self.assertTrue(self.server.run_notifications.called)

    @patch.object(server, 'sleep', AsyncMock())
    @async_test
    async def test_shutdown(self):

        sleep_mock = AsyncMock()

        self.server.add_running_task()

        async def sleep(t):
            self.server.remove_running_task()
            await sleep_mock()

        server.sleep = sleep
        await self.server.shutdown()
        self.assertTrue(sleep_mock.called)

    @async_test
    async def test_run(self):
        self.server._handle_notifications = AsyncMock(
            spec=self.server._handle_notifications)

        await self.server.run()
        self.assertTrue(self.server._handle_notifications.called)

    def test_sync_shutdown(self):
        self.server.shutdown = AsyncMock()
        self.server.sync_shutdown()
        self.assertTrue(self.server.shutdown.called)


class NotificationsProtocolTest(TestCase):
    def setUp(self):
        self.protocol = server.NotificationsProtocol(Mock())

    @async_test
    async def tearDown(self):
        await server.Notification.drop_collection()

    @async_test
    async def test_client_connected_bad_action(self):
        self.protocol.action = 'bad'

        with self.assertRaises(AssertionError):
            await self.protocol.client_connected()

    @patch.object(server.NotificationsProtocol, 'send_response', AsyncMock(
        spec=server.NotificationsProtocol.send_response))
    @async_test
    async def test_client_connected_action_error(self):
        logging.disable(logging.CRITICAL)
        self.protocol.action = 'enable-notification'

        try:
            r = await self.protocol.client_connected()

            self.assertTrue(self.protocol.send_response.called)
            self.assertIs(r, False)
        finally:
            logging.disable(logging.NOTSET)

    @patch.object(server.NotificationsProtocol, 'send_response', AsyncMock(
        spec=server.NotificationsProtocol.send_response))
    @async_test
    async def test_enable_notification(self):
        obj_id = ObjectId()
        self.protocol.action = 'enable-notification'
        self.protocol.data = {}
        self.protocol.data['body'] = {'repository_id': str(obj_id),
                                      'webhook_url': 'https://bla.nada',
                                      'name': 'custom-webhook'}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        qs = Notification.objects.filter(repository_id=str(obj_id))
        count = await qs.count()
        self.assertEqual(count, 1)

    @patch.object(server.NotificationsProtocol, 'send_response', AsyncMock(
        spec=server.NotificationsProtocol.send_response))
    @async_test
    async def test_disable_notification(self):
        obj_id = ObjectId()
        notification_cls = Notification.get_plugin('custom-webhook')
        data = {'repository_id': str(obj_id),
                'webhook_url': 'https://bla.nada'}
        notification = notification_cls(**data)
        await notification.save()

        self.protocol.action = 'disable-notification'
        self.protocol.data = {}
        self.protocol.data['body'] = {'repository_id': str(obj_id),
                                      'webhook_url': 'https://bla.nada',
                                      'name': 'custom-webhook'}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        qs = Notification.objects.filter(repository_id=str(obj_id))
        count = await qs.count()
        self.assertEqual(count, 0)

    @patch.object(server.NotificationsProtocol, 'send_response', AsyncMock(
        spec=server.NotificationsProtocol.send_response))
    @async_test
    async def test_list_notifications(self):
        self.protocol.action = 'list-notifications'
        self.protocol.data = {'body': {}}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        data = self.protocol.send_response.call_args[1]['body']
        notif = data['notifications']
        self.assertTrue(notif[0]['name'])
        self.assertEqual(len(notif), 3, [n['name'] for n in notif])

    @patch.object(server.NotificationsProtocol, 'send_response', AsyncMock(
        spec=server.NotificationsProtocol.send_response))
    @async_test
    async def test_list_notifications_with_repo_id(self):
        obj_id = ObjectId()
        slack_notif = SlackNotification(webhook_url='https://bla.nada',
                                        repository_id=str(obj_id),
                                        statuses=['success', 'fail'])
        await slack_notif.save()

        self.protocol.action = 'list-notifications'
        self.protocol.data = {'body': {'repository_id': str(obj_id)}}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        data = self.protocol.send_response.call_args[1]['body']
        notif = data['notifications']

        for schema in notif:
            if schema['name'] == 'slack-notification':
                self.assertEqual(schema['webhook_url']['value'],
                                 'https://bla.nada')
                self.assertEqual(schema['statuses']['value'][0], 'success')

        self.assertTrue(notif[0]['name'])
        self.assertEqual(len(notif), 3, [n['name'] for n in notif])

    @patch.object(server.NotificationsProtocol, 'send_response', AsyncMock(
        spec=server.NotificationsProtocol.send_response))
    @async_test
    async def test_update_notification(self):
        obj_id = ObjectId()
        slack_notif = SlackNotification(webhook_url='https://bla.nada',
                                        repository_id=str(obj_id),
                                        statuses=['success', 'fail'])
        await slack_notif.save()

        self.protocol.action = 'update-notification'
        self.protocol.data = {'body': {'webhook_url': 'https://bla.tudo',
                                       'repository_id': obj_id,
                                       'name': 'slack-notification'}}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        notif = await SlackNotification.objects.get(repository_id=obj_id)
        self.assertEqual(notif.webhook_url, 'https://bla.tudo')

    @patch.object(server.NotificationsProtocol, 'send_response', AsyncMock(
        spec=server.NotificationsProtocol.send_response))
    @patch.object(server, 'send_email', AsyncMock(spec=server.send_email))
    @async_test
    async def test_send_email(self):
        obj_id = ObjectId()
        slack_notif = SlackNotification(webhook_url='https://bla.nada',
                                        repository_id=str(obj_id),
                                        statuses=['success', 'fail'])
        await slack_notif.save()

        self.protocol.action = 'send-email'
        recipients = ['a@a.com']
        subject = 'something'
        message = 'not really important'

        body = {'recipients': recipients,
                'subject': subject,
                'message': message}
        self.protocol.data = {'body': body}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True
        self.assertTrue(server.send_email.called)


class NotificationsServerTest(TestCase):

    @patch('toxiccore.server.ToxicServer.start')
    def test_notifications_server_lifecycle(self, mock_super_start):
        server_inst = server.NotificationsServer('localhost', 1234)
        self.assertIsInstance(server_inst.output_handler,
                              server.OutputMessageHandler)

        with patch.object(
                server.OutputMessageHandler, 'run', AsyncMock()) as mock_run:
            server_inst.start()
            self.assertTrue(mock_run.called)
            self.assertTrue(mock_super_start.called)

        @async_test
        async def test_shutdown_coro():
            with patch.object(
                    server.OutputMessageHandler,
                    'shutdown', AsyncMock()) as mock_shutdown:
                await server_inst.shutdown()
                self.assertTrue(mock_shutdown.called)

        test_shutdown_coro()
