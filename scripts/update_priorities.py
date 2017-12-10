#!/opt/rh/rh-python36/root/usr/bin/python
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


# To be run once daily (or so), it's rather too expensive to run for every
# allseq update

import logging
LOGGER = logging.getLogger()
logging.basicConfig(level=logging.WARNING)

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported

from mfaliquot.application import SequencesManager

WEBSITEPATH = '/var/www/rechenkraft.net/aliquot2/'

seqinfo = SequencesManager(WEBSITEPATH + "AllSeq.json")

with seqinfo.acquire_lock(block_minutes=5):
     for ali in seqinfo.values():
          ali.calculate_priority()
