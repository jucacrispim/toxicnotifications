# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase

from mongomotor import Document

from toxicnotifications import fields


class PrettyFieldTest(TestCase):

    def setUp(self):

        class TestClass(Document):

            some_attr = fields.PrettyStringField(pretty_name='Some Attribute')

        self.test_class = TestClass

    def test_pretty_name(self):
        self.assertEqual(self.test_class.some_attr.pretty_name,
                         'Some Attribute')
