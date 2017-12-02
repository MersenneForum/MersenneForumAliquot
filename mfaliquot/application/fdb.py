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


# A module with various random fdb interaction needed by allseq.py
# The *goal* is to completely remove any reference to fdb html layout from allseq.py
# This may or may not be achievable.

'''A module to query information from the FactorDatabase, factordb.com.
All functions provided have automatic retries. They return None if there is a
network error of some sort, or False if all retry attempts fail to read valid
data.'''


import logging, re
from ..myutils import blogotubes
from enum import Enum, auto


_logger = logging.getLogger(__name__)

COMPOSITEREGEX = re.compile(r'= <a.+<font color="#002099">[0-9.]+</font></a><sub>&lt;(?P<C>[0-9]+)')
SMALLFACTREGEX = re.compile(r'(?:<font color="#000000">)([0-9^]+)(?:</font></a>)(?!<sub>)')
LARGEFACTREGEX = re.compile(r'(?:<font color="#000000">[0-9^.]+</font></a><sub>&lt;)([0-9]+)')
INFOREGEX = re.compile('<td bgcolor="#BBBBBB">n</td>\n<td bgcolor="#BBBBBB">Digits</td>\n<td bgcolor="#BBBBBB">Number</td>\n</tr><tr><td bgcolor="#DDDDDD">.{1,3}hecked</td>\n<td bgcolor="#DDDDDD">(?P<index>[0-9]+)</td>\n<td bgcolor="#DDDDDD">(?P<size>[0-9]+) <a href="index.php\\?showid=(?P<id>[0-9]+)">\\(show\\)')
CREATEDREGEX = re.compile('([JFMASOND][a-z]{2,8}) ([0-9]{1,2}), ([0-9]{4})') # strftime('%d', strptime(month, "%B"))


################################################################################


class FDBStatus(Enum):
     Unknown = 0
     Prime = auto()
     ProbablyPrime = auto()
     Composite = auto()
     CompositeWithFactors = auto()
     FullyFactored = auto()


def query_id_status(fdb_id, tries=5):
     '''Returns None on network error, False on bad data, or an FDBStatus otherwise.'''
     for i in range(tries):
          page = blogotubes('http://factordb.com/index.php?id='+str(fdb_id))
          if page is None:
               return None
          for s, e in (('PRP', FDBStatus.ProbablyPrime), ('FF', FDBStatus.FullyFactored),
                       ('CF', FDBStatus.CompositeWithFactors), ('C', FDBStats.Composite),
                       ('P', FDBStatus.Prime), ('U', FDBStatus.Unknown)):

               if f"<td>{s}</td>" in page:
                    return e

     return False


################################################################################

def check(old, tries=3, reserves=None, special=None):
     if tries <= 0:
          Print('Bad sequence or id! Seq:', old.seq)
          return old
     if not old or not old.is_valid() or not old.id or special:
          return updateseq(old, reserves)
     # else:
     page = blogotubes('http://factordb.com/index.php?id='+str(old.id))
     if QUITTING: return old
     if 'CF' in page: # Line unfactored, no progress since last update
          old.time = strftime(DATEFMT, gmtime())
          if isinstance(old.progress, int):
               old.progress = id_created(old.id)
          return old
     elif 'FF' in page or 'P' in page:
          return updateseq(old, reserves)
     else:
          return check(old, tries-1, special)






################################################################################


def id_created(i):
     i = str(i)
     #Print('Querying id', i)
     page = blogotubes('http://factordb.com/frame_moreinfo.php?id='+i)
     if page is None:
          return None
     date = CREATEDREGEX.search(page)
     year = date.group(3)
     day = date.group(2)
     if len(day) == 1: day = '0'+day
     month = strftime('%m', strptime(date.group(1), '%B'))
     return '-'.join(iter((year, month, day)))
