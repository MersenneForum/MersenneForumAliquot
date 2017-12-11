#! /usr/bin/env python3
# This is written to Python 3.5 standards
# indentation: 5 spaces (personal preference)
# when making large backwards scope switches (e.g. between def or class blocks)
# use two blank lines for clearer visual separation

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


# The main executable script to drive the primary Aliquot sequences data table.
# Queries information from the FDB and stores the data in a large json table.


################################################################################
# globals/configuration

SLEEPMINUTES = 30 # TODO
LOOPING = False

#
################################################################################


################################################################################
# imports and global initialization

import sys, logging, signal, json
from time import sleep, gmtime, strftime

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot import InterpolatedJSONConfig
from mfaliquot.application import SequencesManager, AliquotSequence, DATETIMEFMT, fdb
from mfaliquot.application.updater import AllSeqUpdater

CONFIG = InterpolatedJSONConfig()
CONFIG.read_file('mfaliquot.config.json')

# logging.config.dictConfig(CONFIG["logging"])
# TODO make default log config file in scripts/
LOGGER = logging.getLogger()
logging.basicConfig(level=logging.INFO)

#
################################################################################

################################################################################
#

def inner_main(updater, seqinfo, special=None):
     LOGGER.info('\n'+strftime(DATETIMEFMT))

     LOGGER.info('Initializing')
     block = 0 if special else CONFIG['blockminutes']

     with seqinfo.acquire_lock(block_minutes=block):

          quitting = updater.do_all_updates(seqinfo, special)


     LOGGER.info('allseq.py update loop complete')
     return quitting


def main():
     global LOOPING, SLEEPING, QUITTING

     try:
          special = [int(arg) for arg in sys.argv[1:]]
     except ValueError:
          print('Error: Args are sequences to be run')
          sys.exit(-1)

     if special:
          LOOPING = False
          # de-duplicate while preserving order
          seen = set()
          seen_add = seen.add # more efficient, tho gain is negligible for small specials
          special = [s for s in special if not (s in seen or seen_add(s))]
     else:
          special = None

     seqinfo = SequencesManager(CONFIG)
     updater = AllSeqUpdater(CONFIG['AllSeqUpdater'])

     # This means you can start it once and leave it, but by setting LOOPING = False you can make it one-and-done
     # This would be a good place for a do...while syntax
     while True:
          quitting = inner_main(updater, seqinfo, special)

          if LOOPING and not quitting:
               LOGGER.info('Sleeping.')
               SLEEPING = True
               sleep(SLEEPMINUTES*60)
               SLEEPING = False
          else:
               break


if __name__ == '__main__':
     try:
          main()
     except BaseException as e:
          LOGGER.exception(f"allseq.py interrupted by {type(e).__name__}: {str(e)}", exc_info=e)
