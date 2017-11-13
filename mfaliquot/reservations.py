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
from time import time, gmtime, strptime, strftime

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
     Python dict. Raises ValueErrors on problems, use str(exception) to get the
     details.'''
     # TODO: Reconsider if the datadict should be read-only, forcing callers
     # to duplicate new reservations onto the datadict
     # Pros: saves the caller duplicate work, IF the caller was using datadict
     # allseq.py uses datadict but only reads reservations, reservations.py
     # writes reservations but doesn't use datadict

     def __init__(self, seqinfo):
          '''`seqinfo` is a reference to the overall data dictionary, to be used
          as a read-only... well, reference. It is not modified by this class.'''
          self._db = dict()
          self._seqinfo = seqinfo #TODO: reconsider
          self._when = None # timestamp written in file #TODO: way to set this


     def _read_res_line(self, line):
          l = line.split()
          seq = AliquotSequence()

          try:
               seq.seq = int(l[0])
          except ValueError:
               try:
                    self._when = strptime(l, DATEFMT)
               except ValueError:
                    return


          try:
               seq.index = int(l[-2])
               seq.size = int(l[-1])
          except ValueError: # Some lines have no data, only <seq name>
               seq.res = ' '.join(l[1:])
          else:
               seq.res = ' '.join(l[1:-2])

          self._db[seq.seq] = seq


     @classmethod
     def read_file(cls, file, seqinfo):
          '''Read a file containing a list of
          `AliquotSequence.reservation_string` entires, ignoring any malformed
          lines. seqinfo is a read-only reference to the overall data'''
          self = cls(seqinfo)
          with open(file, 'r') as f:
               for line in f:
                    self._read_res_line(line)

          Print("Read {} seqs".format(len(self._db)))
          return self


     def write_to_file(self, file):
          '''Write the database to file in `AliquotSequence.reservation_string`
          format'''
          c = 0
          with open(file, 'w') as f:
               f.write(strftime(DATEFMT, self._when)+'\n')
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
                         raise ValueError("Warning: {} already owns {}".format(name, seq))
                    else:
                         raise ValueError("Warning: seq {} is owned by {} but is trying to be reserved by {}!".format(seq, other, name))
               else:
                    if seq not in self._seqinfo:
                         raise ValueError("Warning: {} cannot reserve {}: does not exist".format(name, seq))
                    info = self._seqinfo[seq]
                    # When we read the res db from file, we don't record the other info, so leave it off for consistency
                    self._db[seq] = AliquotSequence(seq=seq, res=name, index=info.index, size=info.size)


     def unreserve_seqs(self, name, seqs):
          '''Mark the `seqs` as no longer reserved. Raises ValueError on any
          of the common problems.'''
          b = c = len(seqs)
          for seq in seqs:
               try:
                    exists = self._db[seq].res == name
               except KeyError:
                    raise ValueError("{} is not reserved at the moment ({})".format(seq, name))
                    continue
               if exists:
                    del self._db[seq]
                    c -= 1
               else:
                    raise ValueError("Warning: Seq {}'s reservation {} doesn't match dropee {}".format(seq, self._db[seq].res, name))

          if c != 0:
               raise ValueError("Only {} seqs were removed, {} were supposed to be dropped".format(b-c, b))


     def apply_reservations_to_seqinfo(self):
          #TODO

















