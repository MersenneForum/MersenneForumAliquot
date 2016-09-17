#!/opt/rh/python33/root/usr/bin/python

# This is written to Python 3.3 standards (may use 3.4 features, I haven't kept track)
# Note: tab depth is 5, as a personal preference


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

JSON = '/var/www/rechenkraft.net/aliquot/AllSeq.json'

################################################################################

from time import strftime
import json

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('.')
# this should be removed when proper pip installation is supported
from mfaliquot.myutils import email, Print

def main():
     Print('Merge finder starting')

     with open(JSON, 'r') as f: # Read current table data
               olddat = json.load(f)['aaData']

     ids = {}
     merged = []
     for ali in olddat:
          this = ali[3] # this = ali.id
          current = ids.get(this) # I'm assuming/hoping this is O(1), i.e. independent of the size of the dict
          if current is None: # No match for this id
               ids[this] = ali[0] # ids[this] = ali.seq # this id corresponds to this seq
          else: # found a match (i.e. a merge)
               seq = ali[0]
               if seq > current:
                    big = seq, current
               else:
                    big = current, seq
               Print(big[0], 'seems to have merged with', big[1])
               merged.append(big)

     if merged:
          try:
               email('Aliquot merge!', '\n'.join('{} seems to have merged with {}'.format(*merge) for merge in merged))
          except Exception as e:
               Print("alimerge email failed")

     Print('Merge finder finished')

if __name__ == '__main__':
     main()
