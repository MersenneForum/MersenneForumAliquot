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
#PIDFILE = argv[0] + '.last_pid'
PIDFILE = 'last_pid'
INFOFILE = '../website/html/AllSeq.json'
MASS_RESERVATIONS = {'yafu@home': 'http://yafu.myfirewall.org/yafu/download/ali/ali.txt.all'}


################################################################################
#
################################################################################


from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported

from mfaliquot.application.reservations import ReservationsSpider
from mfaliquot.application import SequencesManager

import logging
LOGGER = logging.getLogger()
logging.basicConfig(level=logging.INFO) # TODO: add configuration for this (create default config in scripts/)


# Can confirm that the package really should be using a logger, not this adhoc,
# non-live results-to-str nonsense
def inner_main(seqinfo, err):

     if argv[1] == 'add':

          if len(argv[2:]) < 2:
               print("Error: {} add <name> <seq> [<seq>...]".format(argv[0]))
          else:
               LOGGER.info("Add {} seqs".format(len(argv[3:])))
               out = seqinfo.reserve_seqs(argv[2], [int(seq.replace(',','')) for seq in argv[3:]])

     elif argv[1] == 'drop':

          if len(argv[2:]) < 2:
               print("Error: {} drop <name> <seq> [<seq>...]".format(argv[0]))
          else:
               LOGGER.info("Drop {} seqs".format(len(argv[3:])))
               out = seqinfo.unreserve_seqs(argv[2], [int(seq.replace(',','')) for seq in argv[3:]])

     elif argv[1] == 'spider':

          spider = ReservationsSpider(seqinfo, PIDFILE)
          thread_out, mass_out = spider.spider_all_apply_all(MASS_RESERVATIONS)
          for name, addres, dropres in thread_out:
               LOGGER.info(f"{name} successfully added {addres[0]}, dropped {dropres[0]}")

     else:
          print(err)
          exit(-1)


def main():
     err = "Error: commands are 'add', 'drop', or 'spider'"
     if len(argv) < 2:
          print(err)
          exit(-1)

     s = SequencesManager(INFOFILE)

     with s.acquire_lock(block_minutes=3): # reads and inits
          inner_main(s, err)


if __name__ == '__main__':
     main()
