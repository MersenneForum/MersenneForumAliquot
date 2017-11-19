#! /usr/bin/env python3

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

SEQLIST = 'SeqList.txt'

def read_seqlist():
     with open(SEQLIST, 'r') as f:
          return list(int(line) for line in f)


def write_seqlist(seqlist):
     with open(SEQLIST, 'w') as f:
          for seq in seqlist:
               f.write(str(seq)+'\n')


from itertools import zip_longest

def alternate(*iters):
     sentinel = object()
     for tup in zip_longest(*iters, fillvalue=sentinel):
          yield from (x for x in tup if x is not sentinel)

seqlist = set(read_seqlist())

six = {seq for seq in seqlist if seq < 1000000}
seven = seqlist - six
six = list(sorted(six))
seven = list(sorted(seven))

neworder = list(alternate(six, seven))

assert len(neworder) == len(seqlist)

diff = len(seven) - len(six)

print(neworder[:10])
print(diff, neworder[-diff-10:])

write_seqlist(neworder)
