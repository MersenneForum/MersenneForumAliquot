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
from ..myutils import blogotubes

# First the standalone func that processes mass text file reservations
def parse_mass_reservation(reservee, url):
     '''Parses a '\n' separated list of sequences, to be reserved to the given
     name. Returns (current_entries, duplicate_seqs, unknown_lines)'''
     #global email_msg
     txt = blogotubes(url)
     current, dups, unknowns = set(), [], []
     for line in txt.splitlines():
          if SEQ_REGEX.match(line):
               seq = int(line)
               if seq in current:
                    dups.append(seq)
               else:
                    current.add(seq)
          elif not re.match(r'^[0-9]+$', line):
               unknowns.append(line)
     return current, dups, unknowns


def update_apply_all_res(seqinfo, last_pid, mass_reses):
     '''Searches all known reservations, returning compiled reses to be applied,
     as well as various results from subordinate functions'''

     last_pid, prev_pages, all_res = spider_res_thread(last_pid)

     mass_reses_out = []
     for reservee, url in mass_reses:
          current, dups, unknowns = parse_mass_reservation(reservee, url)
          old = set(ali.seq for ali in seqinfo.values() if ali.res == reservee)
          drops = old - current
          adds = current - old
          if drops:
               dropres = seqinfo.unreserve_seqs(reservee, drops)
          else:
               dropres = ()
          all_res.append(reservee, adds, ())
          mass_reses_out.append((reservee, dups, unknowns, dropres))

     out = []
     for name, adds, drops in all_res:
          addres, dropres = (), ()
          if adds:
               addres = seqinfo.reserve_seqs(name, adds)
          if drops:
               dropres = seqinfo.unreserve_seqs(name, drops)
          out.append((name, addres, dropres))

     return last_pid, prev_pages, out, mass_reses_out # What a mess of data


def update_apply_all_res_to_str(last_pid_changed, prev_pages, out, mass_reses_out):
     '''As much for simply reference as for actual use. This entire "return
     enormously nested tuples of retvals to be parsed by scripts into strings"
     thing is, I'm pretty sure, totally crazy'''
     s = 'No new posts!' if last_pid_changed else ''
     if not last_pid_changed and prev_pages:
          raise RuntimeError("No posts but checked previous page???")
     s += '\n'.join("Looks like posts were missed, checking page {}".format(pg) for pg in prev_pages)

     for name, ares, dres in out:
          s += reserve_seqs_to_str(name, *ares)
          s += unreserve_seqs_to_str(name, *dres)

     for name, dups, unknowns, dres in mass_reses_out:
          s += '\n'.join("Warning: mass res-er {} listed a duplicate for {}".format(name, seq) for seq in dups) + '\n' +\
          s += '\n'.join("Warning: unknown line from {}: '{}'".format(name, line) for line in unknowns) + '\n' +\
          s += unreserve_seqs_to_str(name, *dres)


def reserve_seqs_to_str(name, DNEs, already_owns, other_owns):
     return '\n'.join("Warning: {} doesn't exist ({})".format(seq, name) for seq in DNEs) + '\n' + \
            '\n'.join("Warning: {} already owns {}".format(name, seq) for seq in already_owns) + '\n' +\
            '\n'.join("Warning: {} is owned by {} but is trying to be reserved by {}!".format(seq, other, name) for seq, other in other_owns) + '\n'

def unreserve_seqs_to_str(name, DNEs, not_reserveds, wrong_reserveds):
     return '\n'.join("Warning: {} doesn't exist ({})".format(seq, name) for seq in DNEs) + '\n' + \
            '\n'.join("Warning: {} is not currently reserved ({})".format(seq, name) for seq in not_reserveds) + '\n' +\
            '\n'.join("Warning: {} is reserved by {}, not dropee {}!".format(seq, other, name) for seeq, other in wrong_reserveds) + '\n'


