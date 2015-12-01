#! /usr/bin/python3

JSON = '../html/AllSeq.json'

################################################################################

from time import strftime
import json

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot.myutils import email, Print


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

try:
     email('Aliquot merge!', '\n'.join('{} seems to have merged with {}'.format(*merge) for merge in merged))
except Exception as e:
     Print("alimerge email failed")

Print('Merge finder finished')
