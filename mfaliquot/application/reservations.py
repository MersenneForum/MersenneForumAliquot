# This is written to Python 3.3 standards
# indentation: 5 spaces (personal preference)
# when making large scope switches (e.g. between def or class blocks) use two
# blank lines for clear visual separation

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


################################################################################
# This module contains the primary reservation spidering and update logic
# It delegates heavily to forum_xaction for such

from .forum_xaction import spider_res_thread, SEQ_REGEX



















# TODO: Move this out of forum_xaction.py
# First the standalone func that processes mass text file reservations
def _parse_mass_reservation(reservee, url):
     '''Parses a '\n' separated list of sequences, to be reserved to the given name'''
     #global email_msg
     old = {seq.seq for seq in db.values() if seq.res == reservee}
     txt = blogotubes(url)
     current = set()
     for line in txt.splitlines():
          if seq_regex.match(line):
               seq = int(line)
               if seq in current:
                    string = "Duplicate sequence? {} {}".format(seq, url)
                    Print(string)
                    email_msg += string+'\n'
               else:
                    current.add(seq)
          elif not re.match(r'^[0-9]+$', line):
               string = "Unknown line from {}: {}".format(url, line)
               Print(string)
               email_msg += string+'\n'
     # easy peasy lemon squeezy
     done = old - current
     new = current - old
     if done or new:
          spider_msg.append('{}: Add {}, Drop {}'.format(reservee, len(new), len(done)))
          drop_db(db, reservee, done)
          add_db(db, reservee, new)
