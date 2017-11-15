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
from mfaliquot.sequence import AliquotSequence

DATEFMT = '%Y-%m-%d %H:%M:%S'


################################################################################


class AliquotReservations:
     '''A class to interface with the local reservations file. The local file is
     identical to the MF posts in format, namely just a bunch of text lines
     whose format is specified by the `AliquotSequence.reservation_string`
     method. This class merely translates between a list of reslines and a
     Python dict. Methods return a list of error/info messages.'''

     def __init__(self):
          self._db = dict()
          self._when = None # timestamp written in file


     def set_timestamp(self):
          '''Sets the timestamp written to file be "now".'''
          self._when = gmtime()


     def _read_res_line(self, line):
          l = line.split()

          try:
               seq = int(l[0])
          except ValueError:
               try:
                    self._when = strptime(line.strip(), DATEFMT)
               except ValueError:
                    pass
               return

          try:
               int(l[-2])
               int(l[-1])
          except ValueError: # Some lines have no data, only <seq name>
               name = ' '.join(l[1:])
          else:
               name = ' '.join(l[1:-2])

          self._db[seq] = name


     @classmethod
     def read_file(cls, file):
          '''Read a file containing a list of
          `AliquotSequence.reservation_string` entires, ignoring any malformed
          lines. Returns a tuple of (instance, num_read)'''
          self = cls()
          with open(file, 'r') as f:
               for line in f:
                    self._read_res_line(line)

          return self, len(self._db)



     def write_to_file(self, file, seqinfo=None):
          '''Write the database to file in `AliquotSequence.reservation_string`
          format. If you want the traditional size and index info to be there,
          pass the optional seqinfo argument. If passed, a ValueError will be
          raised if seqinfo's reservation info doesn't match (call
          `apply_to_seqinfo` before writing to file). Returns the number of
          reservations recorded.'''
          c = 0
          with open(file, 'w') as f:
               f.write(strftime(DATEFMT, self._when)+'\n')
               if seqinfo:
                    for seq, name in sorted(self._db.items(), key=lambda item: item[0]):
                         if name != seqinfo[seq].res:
                              raise ValueError("Seq {} has new reservation {} but old reservation '{}'".format(seq, name, seqinfo[seq].res))
                         f.write(seqinfo[seq].reservation_string())
                         c += 1
               else:
                    for seq, name in sorted(self._db.items(), key=lambda item: item[0]):
                         f.write("{:>6d}  {:30s}\n".format(seq, name))
                         c += 1
          return c


     def reserve_seqs(self, name, seqs):
          '''Mark the `seqs` as reserved by `name`. Cannot check if a given seq
          actually exists. Returns (list_of_already_owns, list_of_other_owns)'''
          already_owns, other_owns = [], []
          for seq in seqs:
               if seq in self._db:
                    other = self._db[seq]
                    if name == other:
                         already_owns.append(seq)
                    else:
                         other_owns.append((seq, other))
               else:
                    self._db[seq] = name

          return already_owns, other_owns


     def unreserve_seqs(self, name, seqs):
          '''Mark the `seqs` as no longer reserved. Returns (not_reserveds,
          wrong_reserveds, count_dropped) '''
          not_reserveds, wrong_reserveds = [], []
          c = 0
          for seq in seqs:
               try:
                    exists = self._db[seq] == name
               except KeyError:
                    not_reserveds.append(seq)
                    continue

               if exists:
                    del self._db[seq]
                    c += 1
               else:
                    wrong_reserveds.append((seq, self._db[seq]))

          return not_reserveds, wrong_reserveds, c


     def apply_to_seqinfo(self, seqinfo):
          '''Update the seqinfo dict so that all Sequence objects have the
          correct reservation. Returns the count of adds and drops.'''
          # The first one is expensive-ish, rest are cheap-ish
          old = {seq for seq, Seq in seqinfo.items() if Seq.res}
          cur = set(self._db.keys())
          adds  = cur - old
          drops = old - cur
          print(sorted(old), sorted(cur), sorted(adds), sorted(drops))
          for seq in adds:
               seqinfo[seq].res = self._db[seq]
          for seq in drops:
               seqinfo[seq].res = ''
          return len(adds), len(drops)

