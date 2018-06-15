#
# Copyright 2018 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
""" Disable blocks module """

import click

from ..core import ModToolDisable
from .base import common_params, block_name, run

@click.command('disable', short_help=ModToolDisable.description)
@common_params
@block_name
def cli(**kwargs):
    """Disable a block (comments out CMake entries for files)"""
    kwargs['cli'] = True
    self = ModToolDisable(**kwargs)

    if self._info['pattern'] is None:
        self._info['pattern'] = input('Which blocks do you want to disable? (Regex): ')
    if not self._info['pattern'] or self._info['pattern'].isspace():
        self._info['pattern'] = '.'

    run(self)
