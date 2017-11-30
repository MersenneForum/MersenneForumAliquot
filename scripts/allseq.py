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
#


import sys, logging
from time import sleep

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot.application import SequencesManager, DATETIMEFMT, fdb
from mfaliquot.application.reservations import ReservationsSpider

LOGGER = logging.getLogger()
logging.basicConfig() # TODO make default log config file in scripts/

SLEEPING = QUITTING = False


#
################################################################################


################################################################################
#

def read_drop_file():
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


#
################################################################################


################################################################################
#

def main_update_loop(seqinfo, seqs_todo):

     # Main loop
     count = 0
     for seq in seqs_todo:
          #ali = check(seq, seqinfo) # TODO

          #if not ali or not ali.is_valid():
          #     del data_dict[seq]
          #data_dict[seq] = ali

          if QUITTING:
               break

          count += 1
          LOGGER.info('{} sequence{} complete: {}'.format(count, 's' if count > 1 else ' ', ali.seq))
          sleep(0.5) # Different from previous version!


def inner_main(seqinfo, special=None):
     LOGGER.info('\n'+strftime(DATETIMEFMT))

     LOGGER.info('Initializing')
     block = 0 if special else BLOCKMINUTES

     with seqinfo.acquire_lock(block_minutes=block):

          drops = read_drop_file()
          if drops:
               seqinfo.drop(drops)
               seqinfo.write() # "Atomic"
               open(DROPFILE, 'w').close() # leave blank file on filesystem for forgetful humans :)

          seqs_todo = special if special else seqinfo.pop_n_todo(BATCHSIZE)
          LOGGER.info('Init complete, starting FDB queries')

          main_update_loop(seqinfo, seqs_todo)

          LOGGER.info('Update loop complete. Searching for merges...')

          merges = seqinfo.find_and_drop_merges()
          if merges:
               # not really a warning, but noteworthy enough e.g. to trigger an email
               LOGGER.warning("Found merges!")
               for target, drops in merges:
                    LOGGER.warning('The seq(s) {} seem(s) to have merged with {}'.format(', '.join(str(d) for d in drops), target))
          else:
               LOGGER.info("No merges found")

          LOGGER.info('Creating statistics...')
          create_stats_write_html(seqinfo)

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
          try:
               inner_main(seqinfo, special)
          except Exception:
               raise # Errors are unhandled except to interrupt a sleeping loop, and to cleanup via finally

          if LOOPING and not QUITTING:
               LOGGER.info('Sleeping.')
               SLEEPING = True
               sleep(SLEEPMINUTES*60)
               SLEEPING = False
          else:
               break


if __name__ == '__main__':
     main()
