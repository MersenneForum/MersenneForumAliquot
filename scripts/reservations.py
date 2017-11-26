#! /usr/bin/env python3

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

# Run from a cron file like "reservations.py spider" however often to parse
# the MF thread and update its head post.
# The very first run only checks the most recent page of reservation posts, since
# there isn't yet a record of last post checked


################################################################################


from sys import argv, exit
PIDFILE = argv[0] + '.last_pid'
#INFOFILE = '../website/html/AllSeq.json'
INFOFILE = '../mfaliquot/application/AllSeq.json'
MASS_RESERVATIONS = {'yafu@home': 'http://yafu.myfirewall.org/yafu/download/ali/ali.txt.all'}


################################################################################

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported

from mfaliquot.application import reservations as R
from mfaliquot.application import SequencesManager
from mfaliquot.myutils import email, Print

email_msg = ''

def Print_and_email(s):
     global email_msg
     email_msg += s + '\n'
     Print(s)


# Can confirm that the package really should be using a logger, not this adhoc,
# non-live results-to-str nonsense
def inner_main(seqinfo, err):

     if argv[1] == 'add':

          if len(argv[2:]) < 2:
               Print("Error: {} add <name> <seq> [<seq>...]".format(argv[0]))
          else:
               Print("Add {} seqs".format(len(argv[3:])))
               out = seqinfo.reserve_seqs(argv[2], [int(seq.replace(',','')) for seq in argv[3:]])
               for line in R.reserve_seqs_to_str(argv[2], *out).splitlines():
                    Print_and_email(line)

     elif argv[1] == 'drop':

          if len(argv[2:]) < 2:
               Print("Error: {} drop <name> <seq> [<seq>...]".format(argv[0]))
          else:
               Print("Drop {} seqs".format(len(argv[3:])))
               out = seqinfo.unreserve_seqs(argv[2], [int(seq.replace(',','')) for seq in argv[3:]])
               for line in R.unreserve_seqs_to_str(argv[2], *out).splitlines():
                    Print_and_email(line)

     elif argv[1] == 'spider':
          try:
               with open(PIDFILE, 'r') as f:
                    last_pid = int(f.read())
          except FileNotFoundError:
               last_pid = None

          # This shit is crazy, definitely using logging next time
          out = list(R.update_apply_all_res(seqinfo, last_pid, MASS_RESERVATIONS))
          last_pid_changed = (out[0] != last_pid)
          last_pid = out[0]
          out[0] = last_pid_changed
          for line in R.update_apply_all_res_to_str(*out).splitlines():
               Print_and_email(line)

          with open(PIDFILE, 'w') as f:
               f.write(str(last_pid) + '\n')

     else:
          print(err)
          exit(-1)


def main():
     err = "Error: commands are 'add', 'drop', or 'spider'"
     if len(argv) < 2:
          print(err)
          exit(-1)

     s = SequencesManager(INFOFILE)

     with s.acquire_lock(block_minutes=5): # reads and inits
          inner_main(s, err)

     if email_msg:
          try:
               email('Reservations script warnings', email_msg)
          except Exception as e:
               Print('Email failed:', e)
               Print('Message:\n', email_msg)


if __name__ == '__main__':
     main()
