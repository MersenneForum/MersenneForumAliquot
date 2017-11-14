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

DATEFMT = '%Y-%m-%d %H:%M:%S'

SEQREGEX = re.compile(r'(?<![0-9])[0-9]{5,7}(?![0-9])') # matches only 5-7 digit numbers


################################################################################


class AliquotReservations:
     '''A class to interface with the local reservations file. The local file is
     identical to the MF posts in format, namely just a bunch of text lines
     whose format is specified by the `AliquotSequence.reservation_string`
     method. This class merely translates between a list of reslines and a
     Python dict. Methods return a list of error/info messages.'''
# TODO: Change all "error message" return values into programmatic return vals;
# let the calling parent parse the suitable return vals into appropriate messages
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
                    self._when = strptime(l, DATEFMT)
               except ValueError:
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
          lines. Returns a tuple of (instance, logmessage)'''
          self = cls()
          with open(file, 'r') as f:
               for line in f:
                    self._read_res_line(line)

          return self, "Read {} seqs".format(len(self._db))



     def write_to_file(self, file, seqinfo=None):
          '''Write the database to file in `AliquotSequence.reservation_string`
          format. If you want the traditional size and index info to be there,
          pass the optional seqinfo argument. Returns an info string for
          printing.'''
          c = 0
          with open(file, 'w') as f:
               f.write(strftime(DATEFMT, self._when)+'\n')
               if seqinfo:
                    for seq in sorted(self._db.keys()):
                         f.write(seqinfo[seq].reservation_string())
                         c += 1
               else:
                    for seq, name in sorted(self._db.items(), key=lambda item: item[0]):
                         f.write("{:>6d}  {:15s}\n".format(seq, name))
                         c += 1
          return "Wrote {} seqs".format(c)


     def reserve_seqs(self, name, seqs):
          '''Mark the `seqs` as reserved by `name`. Returns a list of error
          messages. Cannot check if a given seq actually exists.'''
          out = []
          for seq in seqs:
               if seq in self._db:
                    other = self._db[seq].res
                    if name == other:
                         out.append("reserve: {} already owns {}".format(name, seq))
                    else:
                         out.append("reserve: {} is owned by {} but is trying to be reserved by {}!".format(seq, other, name))
               else:
                    self._db[seq] = name

          return out


     def unreserve_seqs(self, name, seqs):
          '''Mark the `seqs` as no longer reserved. Returns a list of error
          messages.'''
          out = []
          b = c = len(seqs)
          for seq in seqs:
               try:
                    exists = self._db[seq] == name
               except KeyError:
                    out.append("unreserve: {} is not reserved at the moment ({})".format(seq, name))
                    continue

               if exists:
                    del self._db[seq]
                    c -= 1
               else:
                    out.append("unreserve: Seq {}'s reservation {} doesn't match dropee {}".format(seq, self._db[seq].res, name))

          if c != 0:
               out.append("unreserve: Only {} seqs were removed, {} were supposed to be dropped".format(b-c, b))

          return out


     def parse_mass_reservation(self, reservee, txt):
          out = []
          old = {seq for seq, name in self._db.items() if name == reservee}
          current = set()
          for line in txt.splitlines():
               if SEQREGEX.match(line):
                    seq = int(line)
                    if seq in current:
                         out.append("Duplicate sequence? {} {}".format(seq, url))
                    else:
                         current.add(seq)
               elif not re.match(r'^[0-9]+$', line):
                    out.append("Unknown line from {}: {}".format(url, line))
          # easy peasy lemon squeezy
          done = old - current
          new = current - old
          if done or new:
               out.append('{}: Add {}, Drop {}'.format(reservee, len(new), len(done)))
               out.extend(self.reserve_seqs(reservee, done))
               out.extend(self.unreserve_seqs(reservee, new))
          return out





