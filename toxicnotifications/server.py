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

from asyncio import ensure_future
from asyncio import get_event_loop
from asyncio import sleep
import traceback
from asyncamqp.exceptions import ConsumerTimeout
from toxiccore.protocol import BaseToxicProtocol
from toxiccore.server import ToxicServer
from toxiccore.utils import LoggerMixin, log
from toxiccommon.exchanges import notifications
from toxicnotifications import Notification, settings
from toxicnotifications.mail import send_email


class OutputMessageHandler(LoggerMixin):
    """Fetchs messages from notification queues and dispatches the
    needed output methods."""

    EXCHANGE = notifications

    def __init__(self, loop=None):
        self._stop_consuming_messages = False
        self._running_tasks = 0
        self.loop = loop or get_event_loop()

    async def run(self):
        ensure_future(self._handle_notifications())

    def add_running_task(self):
        self._running_tasks += 1

    def remove_running_task(self):
        self._running_tasks -= 1

    async def _handle_notifications(self):
        self.log('Handling notifications', level='debug')
        exchange = type(self).EXCHANGE
        async with await exchange.consume(timeout=1000) as consumer:
            while not self._stop_consuming_messages:
                try:
                    msg = await consumer.fetch_message(cancel_on_timeout=False)
                except ConsumerTimeout:
                    continue

                self.log('Got msg {} from {}'.format(
                    msg.body['event_type'], msg.body['repository_id']),
                    level='debug')
                ensure_future(self.run_notifications(msg.body))
                await msg.acknowledge()

            self._stop_consuming_messages = False

    async def shutdown(self):
        self._stop_consuming_messages = True
        while self._running_tasks > 0:
            await sleep(0.5)

    def sync_shutdown(self, signum=None, frame=None):
        self.loop.run_until_complete(self.shutdown())

    async def run_notifications(self, msg):
        """Runs all notifications for a given repository that react to a given
        event type.

        :param msg: The incomming message from a notification"""

        repo_id = msg['repository_id']
        event_type = msg['event_type']

        notifications = Notification.get_repo_notifications(repo_id,
                                                            event_type)
        self.log('Running notifications for event_type {}'.format(event_type),
                 level='debug')

        async for notification in notifications:  # pragma no branchs
            # stupid coverage
            self.add_running_task()
            t = ensure_future(notification.run(msg))
            t.add_done_callback(lambda r: self.remove_running_task())


class NotificationsProtocol(BaseToxicProtocol):

    actions = {'enable-notification',
               'disable-notification',
               'update-notification',
               'list-notifications',
               'send-email'}

    @property
    def encrypted_token(self):  # pragma no cover
        return settings.ACCESS_TOKEN

    async def client_connected(self):
        assert self.action in type(self).actions, 'Bad Action'
        fname = self.action.replace('-', '_')
        try:
            meth = getattr(self, fname)
            await meth()
        except Exception:
            msg = traceback.format_exc()
            self.log(msg, level="error")
            await self.send_response(
                body={self.action: 'error', 'error': msg},
                code=1)
            return False
        else:
            return True

    async def enable_notification(self):
        body = self.data['body']

        notif_name = body.pop('name')
        notification_cls = Notification.get_plugin(notif_name)
        notification = notification_cls(**body)
        await notification.save()

        await self.send_response(body={notif_name: 'enabled'}, code=0)

    async def disable_notification(self):
        body = self.data['body']
        notification_name = body.pop('name')

        notification = await Notification.objects.get(_name=notification_name,
                                                      **body)
        await notification.delete()
        await self.send_response(body={notification_name: 'disabled'}, code=0)

    async def list_notifications(self):
        body = self.data['body']
        repo_id = body.get('repository_id')
        notifications = Notification.list_plugins()
        schemas = [n.get_schema(to_serialize=True) for n in notifications]
        if repo_id:
            notifs = await Notification.objects.filter(
                repository_id=repo_id).to_list()
            self._merge_notif_values(schemas, notifs)
        await self.send_response(body={'notifications': schemas}, code=0)

    async def update_notification(self):
        body = self.data['body']
        notification_name = body.pop('name')
        repo_id = body.pop('repository_id')
        await Notification.objects(
            _name=notification_name, repository_id=repo_id).update_one(
                **body)
        await self.send_response(body={notification_name: 'updated'}, code=0)

    async def send_email(self):
        body = self.data['body']
        recipients = body['recipients']
        subject = body['subject']
        message = body['message']
        await send_email(recipients, subject, message)
        await self.send_response(body={'send-email': True}, code=0)

    def _merge_notif_values(self, schemas, notifs):
        notifs_tb = {n.name: n for n in notifs}
        for schema in schemas:
            try:
                notif = notifs_tb[schema['name']]
            except KeyError:
                continue

            for fname, fconfig in schema.items():
                try:
                    attr = getattr(notif, fname)
                    fconfig['value'] = self._parse_value(attr)
                except TypeError:
                    pass

            schema['enabled'] = True

    def _parse_value(self, value):
        if isinstance(value, list):
            value = [str(v) for v in value]
        else:
            value = str(value)

        return value


class NotificationsServer(ToxicServer):

    PROTOCOL_CLS = NotificationsProtocol


def run_server(addr='0.0.0.0', port=1234, loop=None, use_ssl=False,
               **ssl_kw):  # pragma no cover
    log('Serving at {}'.format(port))
    with NotificationsServer(addr, port, loop, use_ssl, **ssl_kw) as server:
        server.start()
