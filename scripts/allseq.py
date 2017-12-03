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


JSONFILE = #'../website/html/AllSeq.json'
TXTFILE  = #'../website/html/AllSeq.txt'

MAINTEMPLATE  = #'../website/html/template.html'
STATSTEMPLATE = #'../website/html/template2.html'

MAINHTML  = #'../website/html/AllSeq.html'
STATSHTML = #'../website/html/statistics.html'
STATSJSON = #'../website/html/statistics.json'


DROPFILE = ''
TERMFILE = ''

BATCHSIZE = 10 # 110
BLOCKMINUTES = 3
SLEEPMINUTES = 30
LOOPING = False

BROKEN = {}
#BROKEN = {747720: (67, 1977171370480)}
# A dict of tuples of {broken seq: (offset, new_start_val)}


#
################################################################################


################################################################################
# imports and global initialization

import sys, logging, signal
from time import sleep, gmtime
from datetime import timedelta

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot.application import SequencesManager, DATETIMEFMT, fdb
from mfaliquot.application.reservations import ReservationsSpider

LOGGER = logging.getLogger()
logging.basicConfig(level=logging.INFO) # TODO make default log config file in scripts/


SLEEPING = QUITTING = False
def handler(sig, frame):
     LOGGER.error("Recieved signal {}, now quitting".format(sig))
     global QUITTING
     QUITTING = True
     if SLEEPING:
          sys.exit()
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)

#
################################################################################


################################################################################
# utility functions

def read_dropfile():
     try:
          with open(DROPFILE) as f:
               _drops = f.read().split() # split() counts newlines as whitespace too
     except FileNotFoundError:
          return []
     if not _drops:
          return []

     drops = []
     for drop in _drops:
          try:
               drops.append(int(drop))
          except ValueError:
               LOGGER.warning("Ignoring unknown 'drop' entry {}".format(drop))

     return drops


def create_stats_write_html(seqinfo):
     # Now get all the stats (i.e. count all the instances of stuff)
     # It's a bit long, tedious and ugly, but I don't think there's anything for it

     # Create broken sequences HTML
     if BROKEN:
          # horizontal table: create a list of tuples containing each column (i.e. each sequence)
          entries = (('''<a href="http://factordb.com/sequences.php?se=1&aq={}&action=last20">{}</a>'''.format(BROKEN[seq][1], seq), str(BROKEN[seq][0])) for seq in sorted(BROKEN))
          row1, row2 = zip(*entries)
          r1 = ''.join('<td>{}</td>'.format(datum) for datum in row1)
          r2 = ''.join('<td>{}</td>'.format(datum) for datum in row2)
          borken_html = '<table><tr><th scope="row">Sequence</th>{}</tr><tr><th scope="row">Index offset</th>{}</tr></table>'.format(r1, r2)
          unborken_html = ''
     else:
          borken_html = ''
          unborken_html = 'none, at the moment'

     # Read in webpage templates
     with open(MAINTEMPLATE, 'r') as f:
          html = f.read()
     with open(STATSTEMPLATE, 'r') as f:
          stats = f.read()

     html = html.format(seqinfo.resdatetime, unborken_html, borken_html) # Imbue the template with the reservation time and broken sequences

     sizetable, cofactable, guidetable, progtable, lentable, totinc, avginc, totprog, progcent = seqinfo.calc_common_stats()

     stats = stats.format(totinc=totlen/totsiz, avginc=avginc, totprog=totprog, progcent=progcent)

     # Write the statsdata and webpages
     with open(MAINHTML, 'w') as f:
          f.write(html)
     with open(STATSHTML, 'w') as f:
          f.write(stats)
     with open(STATSJSON, 'w') as f:
          f.write(json.dumps({"aSizes": sizetable, "aCofacts": cofactable, "aGuides": guidetable, "aProgress": progtable, "aLens": lentable}).replace('],', '],\n')+'\n')


def guide_description(string):
     """Returns a tuple of (str_of_guide, class_with_powers, is_driver)"""
     guide = get_guide(string, powers=False) # dr is an instance of "Factors"
     guidestring = str(dr) # str specified by "Factors" class
     if guidestring == '2':
          return "Downdriver!", 1, False
     else:
          return guidestring, get_class(string), is_driver(guide=guide)

#
################################################################################


################################################################################
# primary update logic

def check_update(old, special):
     '''Returns (old-or-new ali object, successful_update)'''

     if special or not old or not old.is_minimally_valid() or not old.id:
          return do_update(old)

     status = _fdb_error_handler_wrapper(fdb.query_id_status, old.seq, old.id)
     if not status:
          return old, False

     if status is fdb.FDBStatus.CompositeFullyFactored:
          return do_update(old)
     elif status is fdb.FDBStatus.CompositePartiallyFactored: # no progress since last
          process_no_progress(old)
     elif status is fdb.FDBStatus.Prime:
          LOGGER.warning("got a prime id value?? termination?")
          process_no_progress(old)
     else:
          LOGGER.error("problem: crazy status for most recent id of {seq} ({status})")
          return old, False

     return old, True


def do_update(old):

     if old.seq in BROKEN:
          seq = BROKEN[old.seq][1]
     else:
          seq = old.seq

     ali = _fdb_error_handler_wrapper(fdb.query_parse_seq_status, seq, seq)
     if not ali: # the wrapper has logged it and set QUITTING as necessary
          return old, False

     process_progress(ali, old)

     return ali, True


# TODO: if this whole script is later factored out into mfaliquot.application,
# also factor out these two into AliquotSequence
def process_no_progress(old):
     updatedelta = old.timedelta_since_update()
     if updatedelta > timedelta(hours=12):
          # re-updates within 12 hours don't affect priority (allows carefree manual intervention)
          old.nzilch += 1 # again: better name for this would be much appreciated

     old.time = strftime(DATETIMEFMT, gmtime())
     old.calculate_priority()

     if isinstance(old.progress, int):
               old.progress = fdb.id_created(old.id)


def process_progress(ali, old):

     ali.nzilch = 0
     ali.res = old.res
     ali.progress = ali.index - old.index
     ali.guide, ali.klass, ali.driver = guide_description(ali.factors)

     if old.seq in BROKEN:
          ali.seq = old.seq
          ali.index += BROKEN[old.seq][0]
          ali.progress += BROKEN[old.seq][0]

     if ali.progress <= 0:
          LOGGER.warning("fresh update of {ali.seq} revealed no progress")
          ali.progress = fdb.id_created(ali.id)

     ali.calculate_priority()


def _fdb_error_handler_wrapper(func, seq, *args, **kwargs):
     '''Calling the functions in the `fdb` module basically always looks the same:
     catch errors, log them, and return (aliobj, False). Factor that out here.'''
     global QUITTING
     try:
          out = func(*args, **kwargs)
     except fdb.FDBResourceLimitReached as e:
          LOGGER.exception(str(e), exc_info=e)
          QUITTING = True
          return None
     except fdb.FDBDataError as e: # wish these fell through like C switch() statements
          LOGGER.exception(str(e), exc_info=e)
          LOGGER.info("Skipping sequence {seq}")
          return None
     if status is None:
          QUITTING = True
          return None

     return out

#
################################################################################


################################################################################
# primary loop logic

def preloop_initialize(seqinfo, special=None):

     drops = read_dropfile()
     if drops:
          seqinfo.drop(drops)
          seqinfo.write() # "Atomic"
          open(DROPFILE, 'w').close() # leave blank file on filesystem for forgetful humans :)

     ##########

     if special:
          seqs_todo = special
     else:
          n = BATCHSIZE
          from reservations import PIDFILE, MASS_RESERVATIONS # from the sibling script
          thread_out, mass_out = ReservationsSpider(seqinfo, PIDFILE).spider_all_apply_all(MASS_RESERVATIONS)
          seqinfo.write() # "Atomic"
          seqs_todo = [seq for name, addres, dropres in thread_out for seq in addres[0]+dropres[0]]
          if seqs_todo:
               seqinfo.pop_seqs(seqs_todo)
               n -= len(seqs_todo)
          if n > 0:
               seqs_todo.extend(seqinfo.pop_n_todo(n))

          if not seqs_todo:
               raise RuntimeError("Somehow got no seqs todo")

     return seqs_todo


def primary_update_loop(seqinfo, seqs_todo, special=None):

     terminated = []

     count = 0
     for seq in seqs_todo:
          old = seqinfo[seq]

          ali, update_successful = check_update(old, special)

          seqinfo.push_new_info(ali)

          if 'terminated' in ali.factors:
               terminated.append(ali.seq)

          if QUITTING:
               break

          if update_successful:
               count += 1
               LOGGER.info(f'{count} sequence{'s' if count > 1 else ' '} complete: {ali.seq}')

          sleep(1)

     return count, terminated


def postloop_finalize(seqinfo, terminated):

     LOGGER.info("Searching for merges...")
     merges = seqinfo.find_and_drop_merges()
     if merges:
          # not really a warning, but noteworthy enough e.g. to trigger an email
          LOGGER.warning("Found merges!") # LOGGER.notable()
          for target, drops in merges:
               LOGGER.warning('The seq(s) {} seem(s) to have merged with {}'.format(', '.join(str(d) for d in drops), target)) # LOGGER.notable()
     else:
          LOGGER.info("No merges found")

     if terminated:
          LOGGER.warning("Found some 'terminated' sequences: {str(seq) for seq in terminated}") # LOGGER.notable()
          with open(TERMFILE, 'a') as f:
               f.write(''.join(f'{seq}\n'))

     LOGGER.info('Creating statistics...')
     create_stats_write_html(seqinfo)

#
################################################################################


################################################################################
# TODO: Maybe this inner_main should also be factored out into mfaliquot.application
# I mean, really

def inner_main(seqinfo, special=None):
     LOGGER.info('\n'+strftime(DATETIMEFMT))

     LOGGER.info('Initializing')
     block = 0 if special else BLOCKMINUTES

     with seqinfo.acquire_lock(block_minutes=block):

          seqs_todo = preloop_initialize(seqinfo, special)
          n = len(seqs_todo)

          LOGGER.info('Init complete, starting FDB queries on {n} sequences')

          count, terminated = primary_update_loop(seqinfo, seqs_todo, special)

          msg = f'Primary loop {{}}, successfully updated {count} of {n} sequences, finalizing...'
          if QUITTING:
               LOGGER.warning(msg.format('aborted'))
          else:
               LOGGER.info(msg.format('complete'))

          postloop_finalize(seqinfo, terminated)


     LOGGER.info('Written all data and HTML, saved state and finalized')


def main():
     global LOOPING, SLEEPING, QUITTING

     try:
          special = {int(arg) for arg in sys.argv[1:]}
     except ValueError:
          print('Error: Args are sequences to be run')
          sys.exit(-1)

     if special:
          LOOPING = False
     else:
          special = None

     seqinfo = SequencesManager(JSONFILE, TXTFILE)

     # This means you can start it once and leave it, but by setting LOOPING = False you can make it one-and-done
     # This would be a good place for a do...while syntax
     while True:
          inner_main(seqinfo, special)

          if LOOPING and not QUITTING:
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
          LOGGER.exception("allseq.py interrupted: {}".format(e), exc_info=e)
