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

'''This is the module that contains the AllSeqUpdater class, which contains the
primary logic to interface with the FDB to actually update SequencesManager instances'''

from . import AliquotSequence, fdb
import logging, signal
_logger = logging.getLogger(__name__)


class AllSeqUpdater:
     '''A class to manage the state of updating a batch of sequences from the FDB.
     This is meant to operate solely with an already-locked-and-init-ed SequencesManager
     object, so e.g. if you want to write a sleeping loop around this, you'll need
     to re-instantiate the class each time. The only method that calling code needs to
     worry about is do_all_updates, everything else is an implementation detail.'''

     def __init__(self, seqinfo, config):
          '''`seqinfo` is assumed to be an already-locked-and-init-ed SequencesManager
          object. `config` is the configuration read from file.'''
          self.seqinfo = seqinfo
          #self._jsonfile = pass # something something config
          #self._txtfile = pass
          self._maintemplate = pass
          self._statstemplate = pass
          self._mainhtml = pass
          self._statshtml = pass
          self._statsjson = pass
          self._dropfile = pass
          self._termfile = pass
          self._batchsize = pass
          self._broken = pass

          self.quitting = False

     # excessive? probably. but I qualify it as "better explicit than implicit",
     # and there's *no* reason this data should change post-initialization
     #jsonfile      = property(lambda self: self._jsonfile)
     #txtfile       = property(lambda self: self._txtfile)
     maintemplate  = property(lambda self: self._maintemplate)
     statstemplate = property(lambda self: self._statstemplate)
     mainhtml      = property(lambda self: self._mainhtml)
     statshtml     = property(lambda self: self._statshtml)
     statsjson     = property(lambda self: self._statsjson)
     dropfile      = property(lambda self: self._dropfile)
     termfile      = property(lambda self: self._termfile)
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

          drops = []
          for drop in _drops:
               try:
                    drops.append(int(drop))
               except ValueError:
                    _logger.warning("Ignoring unknown 'drop' entry {}".format(drop))

          return drops


     def check_special_for_new_seqs(self, special):
          news = []
          for seq in special:
               if seq not in self.seqinfo:
                    if seq <= 276 or seq >= 10**7 or not seq & 1 == 0:
                         raise ValueError(f"new seq {seq} is invalid")
                    news.append(seq)
                    seqinfo.push_new_info(AliquotSequence(seq=seq, index=-1))
          if news:
               _logger.info(f"Adding {len(news)} new seqs: {' '.join(str(s) for s in news)}")
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

     def check_update(self, old):
          '''Returns (old-or-new ali object, successful_update)'''

          if not old or not old.is_minimally_valid() or not old.id:
               return self.do_update(old)

          status = self._fdb_error_handler_wrapper(fdb.query_id_status, old.seq, old.id)
          if not status: # the wrapper has logged it and set self.quitting as necessary
               return old, False

          if status is fdb.FDBStatus.CompositeFullyFactored:
               return self.do_update(old)
          elif status is fdb.FDBStatus.CompositePartiallyFactored: # no progress since last
               old.process_no_progress()
          elif status is fdb.FDBStatus.Prime:
               _logger.warning("seq {old.seq}: got a prime id value?? termination?")
               old.process_no_progress()
          else:
               _logger.error(f"problem: crazy status for most recent id of {old.seq} ({status})")
               return old, False

          return old, True


     def do_update(self, old):
          if old.seq in self.broken:
               seq = self.broken[old.seq][1]
          else:
               seq = old.seq

          ali = self._fdb_error_handler_wrapper(fdb.query_parse_seq_status, seq, seq)
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
               _logger.exception(str(e), exc_info=e)
               self.quitting = True
               return None
          except fdb.FDBDataError as e: # wish these fell through like C switch() statements
               _logger.exception(str(e), exc_info=e)
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
               self.check_special_for_new_seqs(special)
               self.seqinfo.write() # "Atomic"
               seqs_todo = special
          else:
               seqs_todo = seqinfo.pop_n_todo(BATCHSIZE)

          _logger.debug(f"got {len(seqs_todo)} sequences: {' '.join(str(s) for s in seqs_todo)}")
          return seqs_todo


     def primary_update_loop(self, seqs_todo):
          count, terminated = 0, []
          for seq in seqs_todo:
               old = self.seqinfo[seq]
               ali, update_successful = self.check_update(old)
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
          _logger.info("Searching for merges...")
          merges = seqinfo.find_and_drop_merges()
          if not merges:
               _logger.info("No merges found")

          if terminated:
               _logger.info(f"Writing terminations to {TERMFILE}: {' '.join(str(seq) for seq in terminated)}")
               with open(TERMFILE, 'a') as f:
                    f.write(''.join(f'{seq}\n' for seq in terminated))

          _logger.info(f'Currently have {len(seqinfo)} sequences on file.')
          _logger.info('Creating statistics...')
          create_stats_write_html(seqinfo)
          _logger.info('Statistics written')


     def do_all_updates(self, special=None):
          '''The only method that external code needs to call.'''
          seqs_todo = self.preloop_initialize(special)
          n = len(seqs_todo)

          _logger.info(f'Init complete, starting FDB queries on {n} sequences')

          self._install_handlers()
          count, terminated = self.primary_update_loop(seqs_todo)
          self._reset_handlers()

          msg = f'Primary loop {{}}, successfully updated {count} of {n} sequences, finalizing...'
          if self.quitting:
               _logger.warning(msg.format('aborted'))
          else:
               _logger.info(msg.format('complete'))

          self.postloop_finalize(terminated)
