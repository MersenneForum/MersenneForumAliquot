#! /usr/bin/env python3

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

# Run from a cron file like "reservations.py spider" however often to parse
# the MF thread and update its head post.
# The very first run only checks the most recent page of reservation posts, since
# there isn't yet a record of last post checked

################################################################################

CONFIGFILE = 'mfaliquot.config.json'
SCRIPTNAME = 'reservations'

################################################################################
#
################################################################################

from sys import argv, exit

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported

from mfaliquot import config_boilerplate
from mfaliquot.application.reservations import ReservationsSpider
from mfaliquot.application import SequencesManager
from mfaliquot.application.updater import AllSeqUpdater

CONFIG, LOGGER = config_boilerplate(CONFIGFILE, SCRIPTNAME)


def do_spider(seqinfo):

     spider = ReservationsSpider(seqinfo, CONFIG['ReservationsSpider'])
     thread_out, mass_out = spider.spider_all_apply_all()
     LOGGER.info("Saving reservation changes to file")
     seqinfo.write() # "Atomic"
     # prepare a list of all res-changed seqs: manual drops, manual updates, mass drops.
     # Overflows get priority 0 (slight race condition with update_priorities.py)
     # TODO: maybe factor this out into the class?
     seqs = [seq for name, addres, dropres, updateres in thread_out for seq in dropres[0]]
     #seqs.extend(seq for name, addres, dropres, updateres in thread_out for seq in addres[0])
     seqs.extend(seq for name, addres, dropres, updateres in thread_out for seq in updateres[0])
     # mass_reses_out = list-of [name, dups, unknowns, dropres, addres]
     seqs.extend(seq for name, _, _, dropres, addres in mass_out for seq in dropres[0])
     #seqs.extend(seq for name, _, _, dropres, addres in mass_out for seq in addres[0])
     if seqs:
          ntodo = CONFIG['ReservationsSpider']['batchsize']
          num = len(seqs)
          LOGGER.info(f"got {num} with completed reservations: setting priority to 0 and immediately updating {min(num, ntodo)}")
          for seq in seqs:
               # These will be overwritten by update_priorities.py if the current batch + later allseq runs fail to complete them
               seqinfo[seq].priority = 0
          seqinfo.write() # "atomic"
          todo = seqs[:ntodo]
          updater = AllSeqUpdater(CONFIG['AllSeqUpdater'])
          updater.do_all_updates(seqinfo, todo)
          LOGGER.info('New-reservation seq updates complete')
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
