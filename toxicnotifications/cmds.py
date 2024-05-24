# -*- coding: utf-8 -*-
# Copyright 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=all

import asyncio
import os
import pkg_resources
import shutil
import sys
from time import sleep
from uuid import uuid4

from toxiccommon import common_setup
from toxiccore.cmd import command, main
from toxiccore.utils import (changedir, log, daemonize as daemon,
                             MonkeyPatcher, set_loglevel)

from toxicnotifications import create_settings_and_connect

PIDFILE = 'toxicnotifications.pid'
LOGFILE = './toxicnotifications.log'


class SettingsPatcher(MonkeyPatcher):
    """Patches the settings from pyrocumulus to use the same settings
    as toxibuild."""

    def patch_pyro_settings(self, settings):
        from pyrocumulus import conf as pyroconf
        self.patch_item(pyroconf, 'settings', settings)


@command
def create(root_dir):
    """Creates a new toxicnotifications environment.

    :param --root_dir: Root directory for toxicnotifications."""

    print('Creating root_dir `{}` for toxicnotifications'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicnotifications.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicnotifications',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicnotifications.conf')
    shutil.copyfile(template_file, dest_file)


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
          conffile=None, loglevel='info', pidfile=PIDFILE):
    """ Starts toxicnotifications.

    :param workdir: Work directory for server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to /dev/null
    :param --stderr: stderr path. Defaults to /dev/null
    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicnotifications.conf``
      inside ``workdir``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicnotifications.pid``
    """

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        _set_conffile_env(workdir, conffile)

        create_settings_and_connect()
        from toxicnotifications import settings

        SettingsPatcher().patch_pyro_settings(settings)

        from pyrocumulus.commands.base import get_command

        sys.argv = ['pyromanager.py', '']

        print('Starting notifications web api on port {}'.format(
            settings.TORNADO_PORT))

        command = get_command('runtornado')()

        command.kill = False
        user_msg = 'Starting Toxicnotifications. Listening on port {}'
        command.user_message = user_msg
        command.daemonize = daemonize
        command.stderr = stderr
        command.asyncio = True
        command.application = None
        command.loglevel = loglevel
        command.stdout = stdout
        command.port = settings.TORNADO_PORT
        command.pidfile = pidfile

        if daemonize:
            daemon(call=run_toxicnotifications,
                   cargs=(loglevel, command), ckwargs={},
                   stdout=stdout, stderr=stderr, workdir=workdir,
                   pidfile=pidfile)
        else:
            with changedir(workdir):
                run_toxicnotifications(loglevel, command)


@command
def stop(workdir, pidfile=PIDFILE, kill=False):
    """ Stops toxicnotifications.

    :param workdir: Work directory for the ui to be killed.
    :param --pidfile: pid file for the process.
    :param kill: If true, send signum 9, otherwise, 15.
    """

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        os.environ['TOXICNOTIFICATIONS_SETTINGS'] = os.path.join(
            workdir, 'toxicnotifications.conf')

        create_settings_and_connect()

        print('Stopping output')

        with changedir(workdir):
            with open(pidfile) as fd:
                pid = int(fd.read())

        sig = 9 if kill else 15
        os.kill(pid, sig)

        if sig != 9:
            print('Waiting for the process shutdown')
            while _process_exist(pid):
                sleep(0.5)

        os.remove(pidfile)


@command
def restart(workdir, pidfile=PIDFILE, loglevel='info'):
    """Restarts toxicnotifications

    The instance of toxicnotifications in ``workdir`` will be restarted.
    :param workdir: Workdir for instance to be killed.
    :param --pidfile: Name of the file to use as pidfile.
    :param --loglevel: Level for logging messages.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True, loglevel=loglevel)


@command
def create_token(workdir, conffile=None):
    """Creates an access token for the notifications api.

    :param workdir: Work directory for server.

    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicnotifications.conf``
      inside ``workdir``."""

    _set_conffile_env(workdir, conffile)

    create_settings_and_connect()

    loop = asyncio.get_event_loop()
    uncrypted_token = loop.run_until_complete(create_auth_token())
    print('Created access token: {}'.format(uncrypted_token))


async def create_auth_token(workdir=None):

    if workdir:
        _set_conffile_env(workdir, None)
        create_settings_and_connect()

    from pyrocumulus.auth import AccessToken, Permission
    from toxicnotifications import Notification

    try:
        token = AccessToken(name='notifications-token-{}'.format(uuid4().hex))
        uncrypted_token = await token.save()
        await Permission.create_perms_to(token, Notification, 'crud')
    finally:
        os.environ['TOXICMASTER_SETTINGS'] = ''

    return uncrypted_token


def output_handler_init(handler):
    """Starts the output server"""

    asyncio.ensure_future(handler.run())
    log('Toxicnotifications is running.')


def run_toxicnotifications(loglevel, tornado_server):
    set_loglevel(loglevel)

    loop = asyncio.get_event_loop()
    from toxicnotifications import settings

    loop.run_until_complete(common_setup(settings))

    from toxicnotifications.server import OutputMessageHandler
    handler = OutputMessageHandler()

    output_handler_init(handler)
    tornado_server.run()
    try:
        loop.run_forever()
    finally:
        handler.sync_shutdown()


def _check_conffile(workdir, conffile):
    """Checks if the conffile is inside workdir."""

    absworkdir = os.path.abspath(workdir)
    absconffile = os.path.abspath(conffile)

    return absconffile.startswith(absworkdir)


def _set_conffile_env(workdir, conffile):
    if conffile:

        is_in_workdir = _check_conffile(workdir, conffile)

        if not is_in_workdir:
            print('Config file must be inside workdir')
            sys.exit(1)

        os.environ['TOXICNOTIFICATIONS_SETTINGS'] = os.path.join(
            workdir, conffile)

    else:
        os.environ['TOXICNOTIFICATIONS_SETTINGS'] = os.path.join(
            workdir, 'toxicnotifications.conf')


def _process_exist(pid):
    try:
        os.kill(pid, 0)
        r = True
    except OSError:
        r = False

    return r


if __name__ == '__main__':
    main()
