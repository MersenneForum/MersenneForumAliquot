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

CONFIGFILE = 'mfaliquot.config.json'
LOGFILE = 'reservations.log'

################################################################################
#
################################################################################

from sys import argv, exit
from time import strftime

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported

from mfaliquot import InterpolatedJSONConfig
from mfaliquot.application.reservations import ReservationsSpider
from mfaliquot.application import SequencesManager, DATETIMEFMT
from mfaliquot.application.updater import AllSeqUpdater

# This block is entirely boilerplate
from logging import getLogger
from logging.config import dictConfig
CONFIG = InterpolatedJSONConfig()
CONFIG.read_file(CONFIGFILE)
logconf = CONFIG['logging']
file_handler = logconf['handlers']['file_handler']
file_handler['filename'] = file_handler['filename'].format(LOGFILE)
# TODO: ^ that's pretty darn ugly, surely there's a better way?
dictConfig(logconf)
LOGGER = getLogger(); LOGGER.info(strftime(DATETIMEFMT))


def do_spider(seqinfo):

     spider = ReservationsSpider(seqinfo, CONFIG['ReservationsSpider'])
     thread_out, mass_out = spider.spider_all_apply_all()
     for name, addres, dropres in thread_out:
          LOGGER.info(f"{name} successfully added {addres[0]}, dropped {dropres[0]}")
     LOGGER.info("Saving reservation changes to file")
     seqinfo.write() # "Atomic"
     # prepare a list of all res-changed seqs: manual drops, then manual adds, then
     # mass drops then mass adds. Overflows get priority 0 (slight race condition
     # with update_priorities.py)
     # TODO: maybe factor this out into the class?
     seqs = [seq for name, addres, dropres in thread_out for seq in dropres[0]]
     seqs.extend(seq for name, addres, dropres in thread_out for seq in addres[0])
     # mass_reses_out = list-of [name, dups, unknowns, dropres, addres]
     seqs.extend(seq for name, _, _, dropres, addres in mass_out for seq in dropres[0])
     seqs.extend(seq for name, _, _, dropres, addres in mass_out for seq in addres[0])
     if seqs:
          ntodo = CONFIG['ReservationsSpider']['batchsize']
          num = len(seqs)
          LOGGER.info(f"got {num} with new reservations: updating {min(num, ntodo)}, remainder set to low priority")
          todo, later = seqs[:ntodo], seqs[ntodo:]
          updater = AllSeqUpdater(CONFIG['AllSeqUpdater'])
          updater.do_all_updates(seqinfo, todo)
          LOGGER.info('New-reservation seq updates complete, writing low priority for remainder')
          for seq in later:
               seqinfo[seq].priority = 0
     LOGGER.info('Reservations spidering is complete')


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

          do_spider(seqinfo)

     else:
          print(err)
          exit(-1)


def main():
     err = "Error: commands are 'add', 'drop', or 'spider'"
     if len(argv) < 2:
          print(err)
          exit(-1)

     s = SequencesManager(CONFIG)

     with s.acquire_lock(block_minutes=CONFIG['blockminutes']): # reads and inits
          inner_main(s, err)


if __name__ == '__main__':
     try:
          main()
     except BaseException as e:
          LOGGER.exception(f"reservations.py interrupted by {type(e).__name__}: {str(e)}", exc_info=e)
     LOGGER.info('\n') # Leaves a blank log-header after each block, but it's still better than no gap
