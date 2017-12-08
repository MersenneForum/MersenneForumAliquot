#!/opt/rh/rh-python36/root/usr/bin/python -u
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

WEBSITEPATH = '/var/www/rechenkraft.net/aliquot2/'

JSONFILE = WEBSITEPATH + 'AllSeq.json'
TXTFILE  = WEBSITEPATH + 'AllSeq.txt'

MAINTEMPLATE  = WEBSITEPATH + 'template.html'
STATSTEMPLATE = WEBSITEPATH + 'template2.html'

MAINHTML  = WEBSITEPATH + 'AllSeq.html'
STATSHTML = WEBSITEPATH + 'statistics.html'
STATSJSON = WEBSITEPATH + 'statistics.json'


DROPFILE = 'allseq.drops.txt'
TERMFILE = 'allseq.terms.txt'

BATCHSIZE = 100
BLOCKMINUTES = 3
CHECK_RESERVATIONS = True

SLEEPMINUTES = 30
LOOPING = False

BROKEN = {}
#BROKEN = {747720: (67, 1977171370480)}
# A dict of tuples of {broken seq: (offset, new_start_val)}


#
################################################################################


################################################################################
# imports and global initialization

import sys, logging, signal, json
from time import sleep, gmtime, strftime

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot.application import SequencesManager, AliquotSequence, DATETIMEFMT, fdb
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
     LOGGER.info(f'Checking {DROPFILE} for seqs to drop')
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


def check_special_for_new_seqs(seqinfo, special):
     news = []
     for seq in special:
          if seq not in seqinfo:
               if seq <= 276 or seq >= 10**7 or not seq & 1 == 0:
                    raise ValueError(f"new seq {seq} is invalid")
               news.append(seq)
               seqinfo.push_new_info(AliquotSequence(seq=seq, index=-1))
     return news


def check_reservations(seqinfo):
     # Returns a list of seqs that were manually [un]reservered
     LOGGER.info("Checking reservations...")
     from reservations import PIDFILE, MASS_RESERVATIONS # from the sibling script TODO: MAJOR HACK
     thread_out, mass_out = ReservationsSpider(seqinfo, PIDFILE).spider_all_apply_all(MASS_RESERVATIONS)
     seqinfo.write() # "Atomic"
     seqs = [seq for name, addres, dropres in thread_out for seq in addres[0]+dropres[0]]
     if seqs:
          LOGGER.info(f"These seqs were manually [un]reserved: {' '.join(str(s) for s in seqs)}")
     return seqs


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

     stats = stats.format(totinc=totinc, avginc=avginc, totprog=totprog, progcent=progcent)

     # Write the statsdata and webpages
     with open(MAINHTML, 'w') as f:
          f.write(html)
     with open(STATSHTML, 'w') as f:
          f.write(stats)
     with open(STATSJSON, 'w') as f:
          f.write(json.dumps({"aSizes": sizetable, "aCofacts": cofactable, "aGuides": guidetable, "aProgress": progtable, "aLens": lentable}).replace('],', '],\n')+'\n')


#
################################################################################


################################################################################
# primary update logic

def check_update(old):
     '''Returns (old-or-new ali object, successful_update)'''

     if not old or not old.is_minimally_valid() or not old.id:
          return do_update(old)

     status = _fdb_error_handler_wrapper(fdb.query_id_status, old.seq, old.id)
     if not status: # the wrapper has logged it and set QUITTING as necessary
          return old, False

     if status is fdb.FDBStatus.CompositeFullyFactored:
          return do_update(old)
     elif status is fdb.FDBStatus.CompositePartiallyFactored: # no progress since last
          old.process_no_progress()
     elif status is fdb.FDBStatus.Prime:
          LOGGER.warning("got a prime id value?? termination?")
          old.process_no_progress()
     else:
          LOGGER.error(f"problem: crazy status for most recent id of {old.seq} ({status})")
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

     broken_index = BROKEN[old.seq][0] if old.seq in BROKEN else None
     ali.process_progress(old, broken_index)

     return ali, True


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
          LOGGER.info(f"Skipping sequence {seq}")
          return None
     if out is None:
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
          LOGGER.info(f"Read seqs to drop from file: {' '.join(str(s) for s in drops)}")
          seqinfo.drop(drops)
          seqinfo.write() # "Atomic"
          open(DROPFILE, 'w').close() # leave blank file on filesystem for forgetful humans :)

     ##########

     if special:
          news = check_special_for_new_seqs(seqinfo, special)
          if news:
               LOGGER.info(f"Adding {len(news)} new seqs: {' '.join(str(s) for s in news)}")
          seqs_todo = special

     elif CHECK_RESERVATIONS:
          seqs_todo = check_reservations(seqinfo)
          n = BATCHSIZE
          if seqs_todo:
               seqinfo.pop_seqs(seqs_todo)
               n -= len(seqs_todo)
          if n > 0:
               seqs_todo.extend(seqinfo.pop_n_todo(n))
          if not seqs_todo:
               raise RuntimeError("Somehow got no seqs todo")
          LOGGER.debug(f"got {len(seqs_todo)} sequences: {' '.join(str(s) for s in seqs_todo)}")

     else: # this case can be logically handled with the code above, but I think it's clearer/cleaner this way
          seqs_todo = seqinfo.pop_n_todo(BATCHSIZE)
          LOGGER.debug(f"got {len(seqs_todo)} sequences: {' '.join(str(s) for s in seqs_todo)}")

     return seqs_todo


def primary_update_loop(seqinfo, seqs_todo, special=None):

     count, terminated = 0, []

     for seq in seqs_todo:
          old = seqinfo[seq]
          ali, update_successful = check_update(old)
          seqinfo.push_new_info(ali)
          if update_successful:
               count += 1
               LOGGER.info(f'{count} sequence{"s" if count > 1 else " "} complete: {ali.seq}')
          if 'terminated' in ali.factors:
               terminated.append(ali.seq)

          if QUITTING:
               break

          sleep(1)

     return count, terminated


def postloop_finalize(seqinfo, terminated):

     LOGGER.info("Searching for merges...")
     merges = seqinfo.find_and_drop_merges()
     if not merges:
          LOGGER.info("No merges found")

     if terminated:
          LOGGER.info(f"Writing terminations to {TERMFILE}: {' '.join(str(seq) for seq in terminated)}")
          with open(TERMFILE, 'a') as f:
               f.write(''.join(f'{seq}\n' for seq in terminated))

     LOGGER.info(f'Currently have {len(seqinfo)} sequences on file.')
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

          LOGGER.info(f'Init complete, starting FDB queries on {n} sequences')

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
          LOGGER.exception(f"allseq.py interrupted by {type(e).__name__}: {str(e)}", exc_info=e)
