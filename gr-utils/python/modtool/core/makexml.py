#
# Copyright 2013 Free Software Foundation, Inc.
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
""" Automatically create XML bindings for GRC from block code """

from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import re
import glob

from ..tools import ParserCCBlock
from ..tools import GRCXMLGenerator
from ..tools import CMakeFileEditor
from ..tools import ask_yes_no
from .base import ModTool, ModToolException


class ModToolMakeXML(ModTool):
    """ Make XML file for GRC block bindings """
    name = 'makexml'
    description = 'Generate XML files for GRC block bindings.'

    def __init__(self, *args, **kwargs):
        ModTool.__init__(self, *args, **kwargs)
        for dictionary in args:
            self._info['pattern'] = dictionary.get('blockname', None)
        # This portion will be covered by the CLI
        if self._cli:
            return
        # kwargs portions will be implemented later
        self.validate()

    def validate(self):
        """ Validates the arguments """
        if not self._info['pattern'] or self._info['pattern'].isspace():
            raise ModToolException("Incorrect blockname (Regex)!")

    def run(self):
        """ Go, go, go! """
        if self._cli:
            print("Warning: This is an experimental feature. Don't expect any magic.")
        # 1) Go through lib/
        if not self._skip_subdirs['lib']:
            if self._info['version'] == '37':
                files = self._search_files('lib', '*_impl.cc')
            else:
                files = self._search_files('lib', '*.cc')
            for f in files:
                if os.path.basename(f)[0:2] == 'qa':
                    continue
                (params, iosig, blockname) = self._parse_cc_h(f)
                self._make_grc_xml_from_block_data(params, iosig, blockname)
        # 2) Go through python/
        # TODO

    def _search_files(self, path, path_glob):
        """ Search for files matching pattern in the given path. """
        files = sorted(glob.glob("%s/%s"% (path, path_glob)))
        files_filt = []
        if self._cli:
            print("Searching for matching files in %s/:" % path)
        for f in files:
            if re.search(self._info['pattern'], os.path.basename(f)) is not None:
                files_filt.append(f)
        if len(files_filt) == 0:
            if self._cli:
                print("None found.")
        return files_filt

    def _make_grc_xml_from_block_data(self, params, iosig, blockname):
        """ Take the return values from the parser and call the XML
        generator. Also, check the makefile if the .xml file is in there.
        If necessary, add. """
        fname_xml = '%s_%s.xml' % (self._info['modname'], blockname)
        path_to_xml = os.path.join('grc', fname_xml)
        # Some adaptions for the GRC
        for inout in ('in', 'out'):
            if iosig[inout]['max_ports'] == '-1':
                iosig[inout]['max_ports'] = '$num_%sputs' % inout
                params.append({'key': 'num_%sputs' % inout,
                               'type': 'int',
                               'name': 'Num %sputs' % inout,
                               'default': '2',
                               'in_constructor': False})
        file_exists = False
        if os.path.isfile(path_to_xml):
            if not self._info['yes']:
                if not ask_yes_no('Overwrite existing GRC file?', False):
                    return
            else:
                file_exists = True
                if self._cli:
                    print("Warning: Overwriting existing GRC file.")
        grc_generator = GRCXMLGenerator(
                modname=self._info['modname'],
                blockname=blockname,
                params=params,
                iosig=iosig
        )
        grc_generator.save(path_to_xml)
        if file_exists:
            self.scm.mark_files_updated((path_to_xml,))
        else:
            self.scm.add_files((path_to_xml,))
        if not self._skip_subdirs['grc']:
            ed = CMakeFileEditor(self._file['cmgrc'])
            if re.search(fname_xml, ed.cfile) is None and not ed.check_for_glob('*.xml'):
                if self._cli:
                    print("Adding GRC bindings to grc/CMakeLists.txt...")
                ed.append_value('install', fname_xml, to_ignore_end='DESTINATION[^()]+')
                ed.write()
                self.scm.mark_files_updated(self._file['cmgrc'])

    def _parse_cc_h(self, fname_cc):
        """ Go through a .cc and .h-file defining a block and return info """
        def _type_translate(p_type, default_v=None):
            """ Translates a type from C++ to GRC """
            translate_dict = {'float': 'float',
                              'double': 'real',
                              'int': 'int',
                              'gr_complex': 'complex',
                              'char': 'byte',
                              'unsigned char': 'byte',
                              'std::string': 'string',
                              'std::vector<int>': 'int_vector',
                              'std::vector<float>': 'real_vector',
                              'std::vector<gr_complex>': 'complex_vector',
                              }
            if p_type in ('int',) and default_v is not None and len(default_v) > 1 and default_v[:2].lower() == '0x':
                return 'hex'
            try:
                return translate_dict[p_type]
            except KeyError:
                return 'raw'
        def _get_blockdata(fname_cc):
            """ Return the block name and the header file name from the .cc file name """
            blockname = os.path.splitext(os.path.basename(fname_cc.replace('_impl.', '.')))[0]
            fname_h = (blockname + '.h').replace('_impl.', '.')
            blockname = blockname.replace(self._info['modname']+'_', '', 1)
            return (blockname, fname_h)
        # Go, go, go
        if self._cli:
            print("Making GRC bindings for %s..." % fname_cc)
        (blockname, fname_h) = _get_blockdata(fname_cc)
        try:
            parser = ParserCCBlock(fname_cc,
                                   os.path.join(self._info['includedir'], fname_h),
                                   blockname,
                                   self._info['version'],
                                   _type_translate
                                  )
        except IOError:
            raise ModToolException("Can't open some of the files necessary to parse {}.".format(fname_cc))

        return (parser.read_params(), parser.read_io_signature(), blockname)
