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


################################################################################
# This module contains the primary reservation spidering and update logic
# It delegates heavily to forum_xaction for such

from .forum_xaction import spider_res_thread, SEQ_REGEX
from . import DATETIMEFMT
from .. import blogotubes
from time import strftime, gmtime
import logging

_logger = logging.getLogger(__name__)


class ReservationsSpider: # name is of debatable good-ness
     '''A class to manage the statefulness of spidering the MersenneForum res
     thread. Delegates the primary spidering logic to the module level functions.'''

     def __init__(self, seqinfo, config):
          '''`seqinfo` should be a SequencesManager instance. It is assumed to
          already have acquired its lock.'''
          self.seqinfo = seqinfo
          self.pidfile = config['pidfile']
          self.mass_reses = config['mass_reservations']


     def spider_all_apply_all(self):
          try:
               with open(self.pidfile, 'r') as f:
                    last_pid = int(f.read())
          except FileNotFoundError:
               last_pid = None

          last_pid, *other = update_apply_all_res(self.seqinfo, last_pid, self.mass_reses)

          if last_pid is not None:
               with open(self.pidfile, 'w') as f:
                    f.write(str(last_pid) + '\n')

          return other[1:] # other[0] == prev_pages


################################################################################


# First the standalone func that processes mass text file reservations
def parse_mass_reservation(reservee, url):
     '''Parses a '\n' separated list of sequences, to be reserved to the given
     name. Returns (current_entries, duplicate_seqs, unknown_lines)'''
     txt = blogotubes(url)
     if not txt:
          _logger.error(f"unable to get mass reservation file for {reservee}")
          return None, None, None
     current, dups, unknowns = set(), [], []
     for line in txt.splitlines():
          if SEQ_REGEX.match(line):
               seq = int(line)
               if seq in current:
                    _logger.warning("mass reservation: mass res-er {} listed a duplicate for {}".format(name, seq))
                    dups.append(seq)
               else:
                    current.add(seq)
          elif not re.match(r'^[0-9]+$', line): # don't remember what purpose this line serves, ignoring any number-shaped thing that isn't a 5-7 digit sequence
               _logger.warning("mass reservation: unknown line from {}: '{}'".format(name, line))
               unknowns.append(line)
     return current, dups, unknowns


def update_apply_all_res(seqinfo, last_pid, mass_reses):
     '''Searches all known reservations, returning compiled reses to be applied,
     as well as various results from subordinate functions'''

     now = strftime(DATETIMEFMT, gmtime())

     last_pid, prev_pages, thread_res = spider_res_thread(last_pid)

     mass_adds = []
     mass_reses_out = []
     for reservee, url in mass_reses.items():
          current, dups, unknowns = parse_mass_reservation(reservee, url)
          if current is None or dups is None or unknowns is None:
               _logger.info(f"skipping reservations from {reservee}")
               continue
          old = set(ali.seq for ali in seqinfo.values() if ali.res == reservee)
          drops = old - current
          adds = current - old
          if adds or drops:
               _logger.info(f"mass reservee {reservee}: add {len(adds)} seqs, drop {len(drops)}")
          else:
               _logger.info(f"no res changes for {reservee}")
          dropres = seqinfo.unreserve_seqs(reservee, drops)
          mass_adds.append((reservee, adds))
          mass_reses_out.append([reservee, dups, unknowns, dropres])

     out = []
     for name, adds, drops, updates in thread_res:
          addres = seqinfo.reserve_seqs(name, adds)
          dropres = seqinfo.unreserve_seqs(name, drops)
          updateres = seqinfo.update_seqs(name, updates)
          out.append((name, addres, dropres, updateres))

     for name_adds, lst in zip(mass_adds, mass_reses_out):
          lst.append(seqinfo.reserve_seqs(*name_adds))

     seqinfo.resdatetime = now

     return last_pid, prev_pages, out, mass_reses_out # What a mess of data
     # mass_reses_out = list-of [name, dups, unknowns, dropres, addres]

