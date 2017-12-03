#! /usr/bin/env python3
# This is written to Python 3.3 standards
# indentation: 5 spaces (personal preference)
# when making large scope switches (e.g. between def or class blocks) use two
# blank lines for clearer visual separation

#    Copyright (C) 2014-2015 Bill Winslow
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
from mfaliquot.application.old_sequence import AliquotSequence as OldSequence
from mfaliquot.application import AliquotSequence, SequencesManager


def read_and_parse_data(file1, reservations=None):
     with open(file1, 'r') as f:
          olddat = json.load(f)['aaData']
     data_dict = {}
     if reservations:
          for dat in olddat:
               ali = OldSequence(lst=dat)
               ali.res = reservations.get(ali.seq, '')
               data_dict[ali.seq] = ali
     else:
          for dat in olddat:
               ali = OldSequence(lst=dat)
               data_dict[ali.seq] = ali
     return data_dict


def translate_json(file1, file2):

     old_data = read_and_parse_data(file1)

     new_data = SequencesManager(file2)
     new_data._lock_init_empty()

     for a in old_data.values():
          new_ali = AliquotSequence(seq=a.seq, size=a.size, index=a.index, guide=a.guide,
                                    factors=a.factors, cofactor=a.cofact, klass=a.clas,
                                    res=a.res, progress=a.progress, time=a.time, id=a.id,
                                    driver=a.driver)

          new_data.push_new_info(new_ali)

     new_data.write_unlock()

     return new_data


if __name__ == '__main__':
     from sys import argv
     translate_json(argv[1], argv[2])



