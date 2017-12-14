#! /usr/bin/env python3
# This is written to Python 3.3 standards
# indentation: 5 spaces (personal preference)
# when making large scope switches (e.g. between def or class blocks) use two
# blank lines for clearer visual separation

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


# To be run once every several hours or so, it's rather too expensive to run for
# every allseq update

CONFIGFILE = 'mfaliquot.config.json'
SCRIPTNAME = 'update_priorities'

################################################################################



from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported

from mfaliquot import config_boilerplate
from mfaliquot.application import SequencesManager

CONFIG, LOGGER = config_boilerplate(CONFIGFILE, SCRIPTNAME)


def main():
     seqinfo = SequencesManager(CONFIG)
     with seqinfo.acquire_lock(block_minutes=CONFIG['blockminutes']):
          LOGGER.info("seqinfo inited, updating priorities...")
          for ali in seqinfo.values():
               ali.calculate_priority()

if __name__ == '__main__':
     try:
          main()
     except BaseException as e:
          LOGGER.exception(f"update_priorities.py interrupted by {type(e).__name__}: {str(e)}", exc_info=e)
     LOGGER.info('\n') # Leaves a blank log-header after each block, but it's still better than no gap
