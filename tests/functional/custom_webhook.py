# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.dev>

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

# Server for custom webhook. Used in functional tests

import asyncio
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import sys
from mando import command, main
from mongomotor import Document
from mongomotor.fields import StringField
from toxiccore.utils import changedir, daemonize as daemon
from tests.functional import TEST_DATA_DIR

LOGFILE = os.path.join(TEST_DATA_DIR, 'customwebhook.log')


class WebHookMessage(Document):
    message = StringField()


class MyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        loop = asyncio.get_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(WebHookMessage(message=body).save())


if __name__ == '__main__':
    @command
    def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
              pidfile=None, loglevel='info', conffile=None):

        server_address = ("", 8123)
        httpd = HTTPServer(server_address, MyHandler)
        print("Servidor rodando em http://localhost:8080")
        daemon(httpd.serve_forever, [], {}, stdout, stderr, workdir, pidfile)

    @command
    def stop(workdir, pidfile=None):

        if not os.path.exists(workdir):
            print('Workdir `{}` does not exist'.format(workdir))
            sys.exit(1)

        workdir = os.path.abspath(workdir)
        with changedir(workdir):
            with open(pidfile) as fd:
                pid = int(fd.read())

        sig = 9
        os.kill(pid, sig)

    main()
