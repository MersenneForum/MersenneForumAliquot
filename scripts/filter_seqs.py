#!/usr/bin/python3.7

# This is written to Python 3.6 standards
# indentation: 5 spaces (eccentric personal preference)
# when making large backwards scope switches (e.g. leaving def or class blocks),
# use two blank lines for clearer visual separation

#    Copyright (C) 2014-2017 Bill Winslow
#
#    This module is a part of the mfaliquot package.
#
#    This program is libre software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#    See the LICENSE file for more details.

import json
from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot import InterpolatedJSONConfig
from mfaliquot.application import SequencesManager

CONFIG = InterpolatedJSONConfig()
CONFIG.read_file('mfaliquot.config.json')


def filter(filt_expr, sort_expr, N, sep):
     filt = lambda ali: eval(filt_expr)
     sort = lambda ali: eval(sort_expr)
     seqinfo = SequencesManager(CONFIG)
     seqinfo.readonly_init()
     out = [ali for ali in seqinfo.values() if filt(ali)]
     out.sort(key=sort)
     out = out[:N]
     #print('\n'.join("{}: {}, {}".format(ali.seq, filt(ali), sort(ali)) for ali in out))
     print(sep.join(str(ali.seq) for ali in out))


def _help(argv):
     return """\n\n{} takes exactly 4 arguments: filter_expr, sort_expr, N, 1-char-delimiter (got {})
filter_expr/sort_expr are python exprs based on "ali", e.g.:
for filtering: "isinstance(ali.progress, int) and ali.progress > 2000" and/or "ali.res and ali.seq > 1000000"
for sorting: "ali.cofact" or "ali.time" (or with a minus sign prepended to reverse)
available attributes on 'ali' are:
'seq', 'size', 'index' ,'id' ,'guide', 'factors', 'cofact', 'clas', 'time', 'progress', 'res', 'driver', 'nzilch', and 'priority'
""".format(argv[0], argv[1:])


def main(argv):
     try:
          assert len(argv) == 5
          filter_expr, sort_expr, N, sep = argv[1], argv[2], int(argv[3]), argv[4]
          assert len(argv[4]) == 1
     except:
          raise ValueError(_help(argv)) from None

     filter(filter_expr, sort_expr, N, sep)


if __name__ == '__main__':
     from sys import argv
     main(argv)
