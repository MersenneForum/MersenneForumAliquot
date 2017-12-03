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
# The goal is to completely remove any reference to fdb html layout from allseq.py

'''A module to query information from the FactorDatabase, factordb.com.
All functions provided have automatic retries. They return None if there is a
network error of some sort, or raise an FDBDataError for bad data.'''


import logging, re
from .. import blogotubes
from . import AliquotSequence, DATETIMEFMT
from enum import Enum, auto
from time import gmtime, sleep

def _blogotubes_with_fdb_useragent(*args, **kwargs):
     kwargs['hdrs'].update({'User-Agent': 'MersenneForum/Dubslow/AliquotSequences'})
     return blogotubes(*args, **kwargs)

_logger = logging.getLogger(__name__)

COMPOSITEREGEX = re.compile(r'= <a.+<font color="#002099">[0-9.]+</font></a><sub>&lt;(?P<C>[0-9]+)')
SMALLFACTREGEX = re.compile(r'(?:<font color="#000000">)([0-9^]+)(?:</font></a>)(?!<sub>)')
LARGEFACTREGEX = re.compile(r'(?:<font color="#000000">[0-9^.]+</font></a><sub>&lt;)([0-9]+)')
INFOREGEX = re.compile('<td bgcolor="#BBBBBB">n</td>\n<td bgcolor="#BBBBBB">Digits</td>\n<td bgcolor="#BBBBBB">Number</td>\n</tr><tr><td bgcolor="#DDDDDD">.{1,3}hecked</td>\n<td bgcolor="#DDDDDD">(?P<index>[0-9]+)</td>\n<td bgcolor="#DDDDDD">(?P<size>[0-9]+) <a href="index.php\\?showid=(?P<id>[0-9]+)">\\(show\\)')
CREATEDREGEX = re.compile('([JFMASOND][a-z]{2,8}) ([0-9]{1,2}), ([0-9]{4})') # strftime('%d', strptime(month, "%B"))


################################################################################

class FDBDataError(Exception): pass

class FDBResourceLimitReached(FDBDataError):
     def __init__(self, msg, fdbpage=None):
          if fdbpage:
               try:
                # pages = re.search(r'>Page requests</td>\n<td[^>]*?>([0-9,]+)</td>', page).group(1)
                # ^ avoid repeating the entire regex 5 times with slight variations. very typo prone.
                retmpl = r'>{}</td>\n<td[^>]*?>{}</td>'
                pages, ids, queries, cputime, when = [
                    re.search(retmpl.format(name, valgroup), page).group(1)
                    for name, valgroup in (
                    (r'Page requests',           r'([0-9,]+)'),
                    (r'IDs created',             r'([0-9,]+)'),
                    (r'Database queries',        r'([0-9,]+)'),
                    (r'CPU \(Wall clock time\)', r'([0-9,.]+) seconds'),
                    (r'Counting since',          r'(.*?)')                  )]
                super().__init__(f"{pages} page reqs, {ids} new ids, {queries} db queries, {cputime}s cpu time since {when}")
               except AttributeError: # some re.search() failed
                    _logger.error('Not only is it refusing requests, but its formatting has changed!')
          super().__init__()


################################################################################

def id_created(i):
     i = str(i)
     #Print('Querying id', i)
     page = _blogotubes_with_fdb_useragent('http://factordb.com/frame_moreinfo.php?id='+i)
     if page is None:
          return None
     date = CREATEDREGEX.search(page)
     year = date.group(3)
     day = date.group(2)
     if len(day) == 1: day = '0'+day
     month = strftime('%m', strptime(date.group(1), '%B'))
     return '-'.join(iter((year, month, day)))


################################################################################


class FDBStatus(Enum):
     Unknown = 0
     Prime = auto()
     ProbablyPrime = auto()
     CompositeNoFactors = auto()
     CompositePartiallyFactored = auto()
     CompositeFullyFactored = auto()


def query_id_status(fdb_id, tries=5):
     '''Returns None on network error, raises FDBDataError on bad data, or an FDBStatus otherwise.'''
     for i in range(tries):
          page = _blogotubes_with_fdb_useragent('http://factordb.com/index.php?id='+str(fdb_id))
          if page is None:
               return None
          if 'Resources used by your IP' in page:
               _logger.error('the FDB is refusing requests')
               raise FDBResourceLimitReached(fdbpage=page)

          for s, e in (('PRP', FDBStatus.ProbablyPrime), ('FF', FDBStatus.FullyFactored),
                       ('CF', FDBStatus.CompositeWithFactors), ('C', FDBStats.Composite),
                       ('P', FDBStatus.Prime), ('U', FDBStatus.Unknown)):

               if f"<td>{s}</td>" in page:
                    return e

     return FDBDataError(f'fdb id {fdb_id} failed to produce a valid status after {tries} tries')


################################################################################


def query_parse_seq_status(seq, tries=5):
     '''Returns None on network error, raises FDBDataError if `tries` consecutive bad data,
     or a new AliquotSequence object if successful'''

     for i in reversed(range(tries)):
          page = _blogotubes_with_fdb_useragent('http://factordb.com/sequences.php?se=1&action=last&aq='+str(seq))
          if page is None:
               return None

          if 'Resources used by your IP' in page: # This is a "permanent"-for-rest-of-script condition, only absolute raises here
               _logger.error(f'Seq {seq}: the FDB is refusing requests')
               raise FDBResourceLimitReached(fdbpage=page)
          # not past the resources limit, temporary data errors:
          try:
               ali = _process_ali_data(seq, page)
          except FDBDataError as e:
               if i <= 0:
                    _logger.exception(f"Seq {seq}: bad data after {tries} tries: {str(e)}", exc_info=e)
                    raise
               else:
                    _logger.warning(str(e))
                    _logger.info(f'Seq {seq}: retrying query ({i} tries left)')
                    sleep(2) # TODO: How reasonable is a 2s delay vs the old 5?
                    continue

          if i < tries-1:
               _logger.info(f'Seq {seq}: retry factors: {ali.factors}')

          return ali


def _process_ali_data(seq, page):
     # I can't believe it took me this long to figure out a way passed the spaghetti.
     # Instead of repeating the conditional error handling code once for each error,
     # which is what a goto would typically be used for in e.g. C, just factor out
     # all that code into a function that unconditionally raises appropriate exceptions
     # and then the monolithic conditional error handling can be just after the function --
     # the function+exceptions == traditional-acceptable goto usage for errors.
     # This is so much cleaner. Thank jeebus.
     info = INFOREGEX.search(page)
     comps = COMPOSITEREGEX.findall(page)
     smalls = SMALLFACTREGEX.findall(page)
     bigs = LARGEFACTREGEX.findall(page)

     if not info:
          raise FDBDataError(f"Seq {seq}: no basic information!")

     ali = AliquotSequence(seq=seq, size=int(info.group('size')), index=int(info.group('index')), id=int(info.group('id')))
     ali.time = strftime(DATETIMEFMT, gmtime())

     if 'Not all factors known' not in page:
          _logger.warning(f'Seq {seq}: strange. Termination?')
          ali.factors = "Reportedly terminated"
          ali.guide, ali.clas, ali.driver = 'Terminated?', -9, True
          ali.progress = 'Terminated?'
          return ali

     if not smalls:
          raise FDBDataError(f'Seq {seq}: no smalls match')

     if '2 *' not in smalls[0] and '2^' not in smalls[0]:
          raise FDBDataError(f'Seq {seq}: no 2 in the smalls!')

     factors = ''; size = 2
     factors += smalls[0]
     for small in smalls[1:]:
          factors += " * "+small
          size += len(small)

     if bigs:
          for big in bigs:
               factors += " * P"+big
               size += int(big)

     if not comps:
          raise FDBDataError(f'Seq {seq}: no comps match')

     for comp in comps:
          factors += ' * C'+comp
          cofactor = int(comp)
          size += cofactor

     if size < 0.9 * ali.size:
          raise FDBDataError(f'Seq {seq}: index: {ali.index}, size: {ali.size}, '
                                      f'garbage factors found: {factors}, cofactor: {cofactor}')

     if cofactor < 65: # FDB will autofactor it (is it 70 digits???)
          # less of an error more of just an un-updated downdriver run
          raise FDBDataError(f'Seq {seq}: small cofactor')

     ali.factors = factors
     ali.cofactor = cofactor
     return ali

