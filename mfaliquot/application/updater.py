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

'''This is the module that contains the AllSeqUpdater class, which contains the
primary logic to interface with the FDB to actually update SequencesManager instances'''

from time import sleep
from subprocess import Popen
from . import AliquotSequence, fdb
import logging, signal, json
_logger = logging.getLogger(__name__)


class AllSeqUpdater:
     '''A class to manage the state of updating a batch of sequences from the FDB.
     The only method that calling code needs to worry about is do_all_updates,
     everything else is an implementation detail.'''

     def __init__(self, config):
          self._maintemplate  = config['maintemplate']
          self._statstemplate = config['statstemplate']
          self._mainhtml      = config['mainhtml']
          self._statshtml     = config['statshtml']
          self._statsjson     = config['statsjson']
          self._dropfile      = config['dropfile']
          self._termfile      = config['termfile']
          self._termscript    = config['termscript']
          self._batchsize     = config['batchsize']
          self._broken        = {int(seq): stuff for seq, stuff in config['broken'].items()}

          self.quitting = False

     # excessive? probably. but I qualify it as "better explicit than implicit",
     # and there's *no* reason this data should change post-initialization
     maintemplate  = property(lambda self: self._maintemplate)
     statstemplate = property(lambda self: self._statstemplate)
     mainhtml      = property(lambda self: self._mainhtml)
     statshtml     = property(lambda self: self._statshtml)
     statsjson     = property(lambda self: self._statsjson)
     dropfile      = property(lambda self: self._dropfile)
     termfile      = property(lambda self: self._termfile)
     termscript    = property(lambda self: self._termscript)
     batchsize     = property(lambda self: self._batchsize)
     broken        = property(lambda self: self._broken)


     def _install_handlers(self):
          def handler(sig, frame):
               _logger.error("Recieved signal {}, now quitting".format(sig))
               nonlocal self
               self.quitting = True
          self._oldsigtermhandler = signal.signal(signal.SIGTERM, handler)
          self._oldsiginthandler  = signal.signal(signal.SIGINT,  handler)

     def _reset_handlers(self):
          signal.signal(signal.SIGTERM, self._oldsigtermhandler)
          signal.signal(signal.SIGINT,  self._oldsiginthandler)


     ###########################################################################
     # utility functions

     def read_dropfile(self):
          _logger.info(f'Checking {self.dropfile} for seqs to drop')
          try:
               with open(self.dropfile) as f:
                    _drops = f.read().split() # split() counts newlines as whitespace too
          except FileNotFoundError:
               return []
          if not _drops:
               return []

          drops = set()
          for drop in _drops:
               try:
                    drop = int(drop)
               except ValueError:
                    _logger.warning("Ignoring unknown 'drop' entry {}".format(drop))
               else:
                    if drop in self.seqinfo and drop not in drops:
                         drops.add(drop)

          return drops


     def add_new_seqs(self, special):
          news = []
          for seq in special:
               if seq not in self.seqinfo:
                    if seq <= 276 or seq >= 10**7 or not seq & 1 == 0:
                         raise ValueError(f"new seq {seq} is invalid")
                    news.append(seq)
                    self.seqinfo.push_new_info(AliquotSequence(seq=seq, index=-1))
          if news:
               _logger.info(f"Added {len(news)} new seqs: {' '.join(str(s) for s in news)}")
               self.seqinfo.write() # "Atomic"
          return news


     def create_stats_write_html(self):
          # Now get all the stats (i.e. count all the instances of stuff)
          # It's a bit long, tedious and ugly, but I don't think there's anything for it

          # Create broken sequences HTML
          if self.broken:
               # horizontal table: create a list of tuples containing each column (i.e. each sequence)
               entries = (('''<a href="http://factordb.com/sequences.php?se=1&aq={}&action=last20">{}</a>'''.format(self.broken[seq][1], seq), str(self.broken[seq][0])) for seq in sorted(self.broken))
               row1, row2 = zip(*entries)
               r1 = ''.join('<td>{}</td>'.format(datum) for datum in row1)
               r2 = ''.join('<td>{}</td>'.format(datum) for datum in row2)
               borken_html = '<table><tr><th scope="row">Sequence</th>{}</tr><tr><th scope="row">Index offset</th>{}</tr></table>'.format(r1, r2)
               unborken_html = ''
          else:
               borken_html = ''
               unborken_html = 'none, at the moment'

          # Read in webpage templates
          with open(self.maintemplate, 'r') as f:
               html = f.read()
          with open(self.statstemplate, 'r') as f:
               stats = f.read()

          html = html.format(self.seqinfo.resdatetime, unborken_html, borken_html) # Imbue the template with the reservation time and broken sequences

          sizetable, cofactable, guidetable, progtable, lentable, totinc, avginc, totprog, progcent = self.seqinfo.calc_common_stats()

          stats = stats.format(totinc=totinc, avginc=avginc, totprog=totprog, progcent=progcent)

          # Write the statsdata and webpages
          with open(self.mainhtml, 'w') as f:
               f.write(html)
          with open(self.statshtml, 'w') as f:
               f.write(stats)
          with open(self.statsjson, 'w') as f:
               f.write(json.dumps({"aSizes": sizetable, "aCofacts": cofactable, "aGuides": guidetable, "aProgress": progtable, "aLens": lentable}).replace('],', '],\n')+'\n')


     ###########################################################################
     # primary update logic

     def update(self, old):
          '''Returns (old-or-new ali object, successful_update)'''

          if not old or not old.is_minimally_valid() or not old.id:
               return self.query_sequence(old)

          status, retval = self._fdb_error_handler_wrapper(fdb.query_id, old.seq, old.id)
          if not status: # the wrapper has logged it and set self.quitting as necessary
               return old, False


          if status is fdb.FDBStatus.CompositeFullyFactored:
               return self.query_sequence(old)

          elif status is fdb.FDBStatus.CompositePartiallyFactored: # no progress since last update
               factors, cofactor = retval
               if factors != old.factors:
                    #_logger.debug(f'Seq {old.seq} index {old.index}, partial progress: parsed {factors!r}, stored {old.factors!r}')
                    old.factors = factors
                    old.cofactor = cofactor
                    old.process_no_progress(partial=True) # Implicit assumption: partial progress won't ever change guide/class
               else:
                    old.process_no_progress()

          elif status is fdb.FDBStatus.Prime:
               _logger.warning(f"seq {old.seq}: got a prime id value?? termination?")
               old.process_no_progress()

          else:
               _logger.error(f"problem: crazy status for most recent id of {old.seq} ({status})")
               return old, False


          return old, True


     def query_sequence(self, old):
          if old.seq in self.broken:
               seq = self.broken[old.seq][1]
          else:
               seq = old.seq

          ali = self._fdb_error_handler_wrapper(fdb.query_sequence, seq, seq)
          if not ali: # the wrapper has logged it and set self.quitting as necessary
               return old, False

          broken_index = self.broken[old.seq][0] if old.seq in self.broken else None
          ali.process_progress(old, broken_index)

          return ali, True


     def _fdb_error_handler_wrapper(self, func, seq, *args, **kwargs):
          '''Calling the functions in the `fdb` module basically always looks the same:
          catch errors, log them, and return (aliobj, False). Factor that out here.'''
          try:
               out = func(*args, **kwargs)
          except fdb.FDBResourceLimitReached as e:
               _logger.error(str(e))
               self.quitting = True
               return None
          except fdb.FDBDataError as e: # wish these fell through like C switch statements
               _logger.error(str(e))
               _logger.info(f"Skipping sequence {seq}")
               return None
          if out is None:
               self.quitting = True
               return None

          return out


     ###########################################################################
     # primary loop logic

     def preloop_initialize(self, special=None):
          drops = self.read_dropfile()
          if drops:
               _logger.info(f"Read seqs to drop from file: {' '.join(str(s) for s in drops)}")
               self.seqinfo.drop(drops)
               self.seqinfo.write() # "Atomic"
               open(self.dropfile, 'w').close() # leave blank file on filesystem for forgetful humans :)

          if special:
               self.add_new_seqs(special)
               seqs_todo = special
          else:
               seqs_todo = tuple(self.seqinfo.pop_n_todo(self.batchsize))

          _logger.debug(f"got {len(seqs_todo)} sequences: {' '.join(str(s) for s in seqs_todo)}")
          return seqs_todo


     def primary_update_loop(self, seqs_todo):
          count, terminated = 0, []
          for seq in seqs_todo:
               old = self.seqinfo[seq]
               ali, update_successful = self.update(old)
               self.seqinfo.push_new_info(ali)
               if update_successful:
                    count += 1
                    _logger.info(f'{count} sequence{"s" if count > 1 else " "} complete: {ali.seq}')
               if 'terminated' in ali.factors:
                    terminated.append(ali.seq)

               if self.quitting:
                    break

               sleep(1)

          return count, terminated


     def postloop_finalize(self, terminated):
          if terminated:
               _logger.warning(f"Writing terminations to {self.termfile}: {' '.join(str(seq) for seq in terminated)}")
               # _logger.notable()
               with open(self.termfile, 'a') as f:
                    f.write(''.join(f'{seq}\n' for seq in terminated))
               self.seqinfo.drop(terminated)
               _logger.info("Launching termination verification script...")
               Popen(self.termscript, start_new_session=True)


          _logger.info("Searching for merges...")
          merges = self.seqinfo.find_and_drop_merges()
          if not merges:
               _logger.info("No merges found")

          _logger.info(f'Currently have {len(self.seqinfo)} sequences on file. Creating statistics...')
          self.create_stats_write_html()
          _logger.info('Statistics written')


     def do_all_updates(self, seqinfo, special=None):
          '''The only method that external code needs to call. `seqinfo` must
          already be locked and initialized. Returns whether or not the loop was
          aborted due to error, or completed normally.'''
          self.seqinfo = seqinfo
          self.quitting = False

          seqs_todo = self.preloop_initialize(special)
          n = len(seqs_todo)

          _logger.info(f'Updater init complete, starting FDB queries on {n} sequences')

          self._install_handlers()
          count, terminated = self.primary_update_loop(seqs_todo)
          self._reset_handlers()

          msg = f'Primary loop {{}}, successfully updated {count} of {n} sequences, finalizing...'
          if self.quitting:
               _logger.warning(msg.format('aborted'))
          else:
               _logger.info(msg.format('complete'))

          self.postloop_finalize(terminated)
          del self.seqinfo
          return self.quitting

