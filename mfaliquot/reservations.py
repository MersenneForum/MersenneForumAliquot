#! /usr/bin/env python3
# indentation: 5 spaces (personal preference)

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

'''A module to maintain a local text file with all aliquot sequence reservations
'''

import re
from time import time, strftime, gmtime

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot.sequence import AliquotSequence
from mfaliquot.myutils import linecount, Print, strftime, blogotubes, add_cookies, email


DIR = '../website/html' # Set this appropriately
LOCALFILE = DIR+'/reservations'
BACKUP = DIR+'/backup'
INFO = DIR+'/AllSeq.txt'
SPECIALRESERVATIONS = {'yoyo@home': 'http://yafu.myfirewall.org/yafu/download/ali/ali.txt.all'}
DATEFMT = '%Y-%m-%d %H:%M:%S'

EMAILMSG = ''


################################################################################


class AliquotReservations:
     '''A class to interface with the local reservations file. The local file is
     identical to the MF posts in format, namely just a bunch of text lines
     whose format is specified by the `AliquotSequence.reservation_string`
     method. This class merely translates between a list of reslines and a
     Python dict.'''

     def __init__(self, seqinfo):
          '''`data` is a reference to the overall data dictionary, to be used
          as... well as a reference. It is not modified by this class.'''
          self._db = dict()
          self._seqinfo = seqinfo


     @staticmethod
     def _read_res_line(line):
          l = line.split()
          seq = AliquotSequence()

          try:
               seq.seq = int(l[0])
          except ValueError:
               # TODO: check for timestamp and read it
               return None

          try:
               seq.index = int(l[-2])
               seq.size = int(l[-1])
          except ValueError: # Some lines have no data, only <seq name>
               seq.res = ' '.join(l[1:])
          else:
               seq.res = ' '.join(l[1:-2])

          return seq


     @classmethod
     def read_file(cls, file):
          '''Read a file containing a list of
          `AliquotSequence.reservation_string` entires, ignoring any malformed
          lines.'''
          self = cls()
          with open(file, 'r') as f:
               for line in f:
                    seq = self._read_res_line(line)
                    if seq:
                         self._db[seq.seq] = seq

          Print("Read {} seqs".format(len(self)))
          return self


     def write_to_file(self, file):
          '''Write the database to file in `AliquotSequence.reservation_string`
          format'''
          c = 0
          with open(file, 'w') as f:
               f.write(strftime(DATEFMT, gmtime())+'\n')
               for seq in sorted(db.keys()):
                    f.write(db[seq].reservation_string())
                    c += 1
          Print("Wrote {} seqs".format(c))


     def reserve_seqs(self, name, seqs):
          '''Mark the `seqs` as reserved by `name`. Raises ValueError on any of
          the common problems with the data'''
          for seq in seqs:
               if seq in self._db:
                    other = self._db[seq].res
                    if name == other:
                         raise ValueError(



          raise ValueError("{} cannot reserve {}: does not exist".format(name, seq))












def add_db(db, name, seqs):
     global email_msg
     for seq in seqs:
          if seq in db:
               other = db[seq].res
               if name == other:
                    string = "Warning: {} already owns {}".format(name, seq)
                    Print(string)
                    email_msg += string+'\n'
               else:
                    string = "Warning: seq {} is owned by {} but is trying to be reserved by {}!".format(seq, other, name)
                    Print(string)
                    email_msg += string+'\n'
          else:
               if info:
                    infos = get_info(seq)
                    if not infos:
                         string = "Warning: {} doesn't appear to be in the list".format(seq)
                         Print(string)
                         email_msg += string+'\n'
                    else:
                         db[seq] = AliquotSequence(seq=seq, res=name, index=infos[0], size=infos[1])



















