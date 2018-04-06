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


CONFIGFILE = 'mfaliquot.config.json'
SCRIPTNAME = 'convert_format'

################################################################################



from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported

from mfaliquot import config_boilerplate
from mfaliquot.application import SequencesManager
from mfaliquot.application.old_sequence import SequenceInfo as OldInfo
from mfaliquot.application.sequence import SequenceInfo

from mfaliquot.theory.aliquot import abundance

CONFIG, LOGGER = config_boilerplate(CONFIGFILE, SCRIPTNAME)


def main():
     seqsmanager = SequencesManager(CONFIG, _sequence_class=OldInfo)
     with seqsmanager.acquire_lock(block_minutes=0):
          LOGGER.info("seqsmanager inited, converting seq format...")
          for seq, ali in seqsmanager.items():
               # we use either ali.seq or ali[0], but for constructor use
               # we need the attrs as dictionary keywords instead
               dct = {kw: getattr(ali, kw) for kw in ali._map}
               newali = SequenceInfo(**dct)
               seqsmanager._data[seq] = newali
               # adjust the following for the specifics of the new SequenceInfo
               newali.set_abundance()


if __name__ == '__main__':
     try:
          main()
     except BaseException as e:
          LOGGER.exception(f"convert_format.py interrupted by {type(e).__name__}: {str(e)}", exc_info=e)
