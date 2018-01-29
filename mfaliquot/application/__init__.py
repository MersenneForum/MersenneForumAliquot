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


################################################################################
#
# This is the central file of the application module, providing the common classes
# used by scripts implementing the procedural stuff.
#
# AliquotSequence is the standard record of information for one single sequence,
# and is the primary ingredient in the AllSeq.json/.html files.
#
# _SequencesData is the (private) class which is in charge of reading and writing
# to the Master Data File, AllSeq.json. It is not intended to be exported. It
# contains the (public) methods which manipulate its private data structures.
#
# SequencesManager subclasses _SequencesData, and implements the common algorithms
# which would be useful to scripts attempting to use the underlying data in the
# file. These algorithms needn't the private data, and for these two reasons is
# it a separate subclass, and also thus exportable. (The public methods of its
# parent are also exposed here.)
#
################################################################################


import json, logging
from ..theory import aliquot as alq
from collections import defaultdict, Counter
from time import sleep, strftime, gmtime
from datetime import datetime, timedelta, date
from os import remove as rm
from contextlib import contextmanager


################################################################################


DATETIMEFMT = '%Y-%m-%d %H:%M:%S'
DATEFMT     = '%Y-%m-%d' # needs to be the same format as returned by fdb.id_created()
_logger = logging.getLogger(__name__)


################################################################################
# First, the AliquotSequence class:

# A common class to multiple scripts. It uses a secret dictionary to map attributes
# to list form, which is handy for trivial JSONification. Perhaps not the best
# design, but the inexperienced me fresh to Python and OOP went power crazy with
# __getattribute__ and __setattr__, and I can certainly think of worse ways of
# doing this

class AliquotSequence(list):
     _map = {'seq':      (0, None), # (list_index, default_val)
             'size':     (1, None),
             'index':    (2, None),
             'guide':    (3, ''),
             'factors':  (4, ''),
             'cofactor': (5, 0),
             'klass':    (6, None),
             'res':      (7, ''),
             'progress': (8, None),
             'time':     (9, ''),
             'priority': (10, 0),
             'id':       (11, None),
             'driver':   (12, None)
            }
     _defaults = [None] * len(_map)
     for attr, tup in _map.items():
          _defaults[tup[0]] = tup[1]


     def __setattr__(self, name, value):
          try:
               # Attributes are secretly just a specific slot on the list
               self[AliquotSequence._map[name][0]] = value
          except KeyError:
               super().__setattr__(name, value)


     def __getattribute__(self, name):
          try:
               return self[AliquotSequence._map[name][0]]
          except KeyError:
               return super().__getattribute__(name)


     def __init__(self, **kwargs):
          '''This recognizes all valid attributes, as well as the 'lst' kwarg
          to convert from list format (must be correct length).'''
          # Not exactly the prettiest code, but it's very general code
          # First super().__init__ as appropriate
          if 'lst' in kwargs:
               l = kwargs['lst']
               a = len(l)
               b = len(self._map)
               if a != b:
                    raise ValueError('AliquotSequence.__init__ received invalid size list (got {}, must be {})'.format(a, b))
               super().__init__(l)
               del kwargs['lst']
          else:
               super().__init__(self._defaults)

          for kw, val in kwargs.items():
               if kw not in self._map:
                    raise TypeError("unknown keyword arugment {}".format(kw))
               self.__setattr__(kw, val)


     def is_minimally_valid(self):
          return self.seq and (self.size and self.size > 0) and (self.index and self.index > 0) and self.factors


     def __str__(self):
          if self.is_minimally_valid():
               return "{:>7d} {:>5d}. sz {:>3d} {:s}".format(self.seq, self.index, self.size, self.factors)
          else:
               raise ValueError('Not fully described! Seq: '+str(self.seq))


     def reservation_string(self):
          '''str(AliquotSequence) gives the AllSeq.txt format, this gives the MF reservations post format'''
          #    966  Paul Zimmermann   893  178
          # 933436  unconnected     12448  168
          if not self.res:
               return ''
          out = "{:>7d}  {:30s} {:>5d}  {:>3d}".format(self.seq, self.res, self.index, self.size)
          return out


     _prio_config = {
          'max_update_period': 90,
          'reservation_update_period': 14,
          'reservation_discount': 1/2,
          'small_cofactor_bound': 90,
          'small_cofactor_discount': 1/120, # actually cofactorsize/120. Must be less than 1/bound
          'downdriver_discount': 1/2,
          'shortterm_penalty_duration': 2, # days below which to apply a penalty
          'shortterm_penalty_initial': 6 # penalty added to newly-updated seqs
     }
     # TODO: figure out how to move the above ^ to the config file


     def calculate_priority(self, **kwargs):
          config = self._prio_config # Saves the attribute lookup a dozen times per call
          config.update(kwargs)

          max_update_period = config['max_update_period']

          last_update_datetime = datetime.strptime(self.time, DATETIMEFMT)
          updatedelta = (datetime.utcnow() - last_update_datetime)
          updatedeltadays = updatedelta/timedelta(days=1)
          # timedelta objects have a .days attribute, but that truncates the seconds
          # "dividing" instead by a unit of days leaves the fractional part on the float

          days_without_movement = 1
          if isinstance(self.progress, str):
               progress_date = date(*[int(s) for s in self.progress.split('-')])
               days_without_movement = (last_update_datetime.date() - progress_date).days

          base_prio = max(0, days_without_movement - updatedeltadays)

          if self.cofactor and self.cofactor < config['small_cofactor_bound']:
               base_prio *= self.cofactor*config['small_cofactor_discount']

          if self.res:
               base_prio *= config['reservation_discount']
               max_update_period = config['reservation_update_period']

          if 'Downdriver' in self.guide:
               base_prio *= config['downdriver_discount']

          if updatedeltadays < config['shortterm_penalty_duration']:
               # Prevent getting overzealous on a single seq in too short a time
               slope = config['shortterm_penalty_initial']/config['shortterm_penalty_duration']
               base_prio += config['shortterm_penalty_initial'] - slope*updatedeltadays
          else:
               # If max_update_period is at least half over, start scaling priority to 0
               ratio = updatedelta/timedelta(days=max_update_period)
               if ratio > 0.5:
                    # f(0.5) = 1, f(1) = 0 --> f(x) = 2 - 2x
                    base_prio *= 2 - 2*ratio

          self.priority = round(base_prio, 2)


     def process_no_progress(self):
          self.time = strftime(DATETIMEFMT, gmtime())

          if isinstance(self.progress, int):
               self.progress = fdb.id_created(self.id)

          self.calculate_priority()


     def process_progress(self, old, broken_offset=None):

          self.res = old.res
          self.progress = self.index - old.index
          self.guide, self.klass, self.driver = self.guide_description()

          if broken_offset:
               self.seq = old.seq
               self.index += broken_offset
               self.progress += broken_offset

          if self.progress == 0 and self.factors != old.factors:
               _logger.info(f"fresh sequence query of {self.seq} revealed smaller cofactor but no progress")
               self.progress = strftime(DATEFMT, gmtime())
          elif self.progress <= 0:
               _logger.info(f"fresh sequence query of {self.seq} revealed no progress")
               self.progress = fdb.id_created(self.id)

          self.calculate_priority()


     def guide_description(self):
          """Returns a tuple of (str_of_guide, class_with_powers, is_driver)"""
          guide = alq.get_guide(self.factors, powers=False) # dr is an instance of "Factors"
          guidestring = str(guide) # str specified by "Factors" class
          if guidestring == '2':
               return "Downdriver!", 1, False
          else:
               return guidestring, alq.get_class(self.factors), alq.is_driver(guide=guide)

#
#
################################################################################


################################################################################
# Next would be _SequenceData, but first two helper pieces: custom_inherit, used
# by _SequencesData to delegate some methods from itself to its underlying
# dictionary, and a thin wrapper class around stdlib.heapq (can't believe that
# doesn't already exist)
#
# First, custom_inherit and its own helper _DelegatedAttribute

# Following class and decorator totally jacked from Jacob Zimmerman, with a few tweaks/renames
# https://programmingideaswithjake.wordpress.com/2015/05/23/python-decorator-for-simplifying-delegate-pattern/
#
# I couldn't get the default copying of the entire baseclass dict to work, because that delegates __new__,
# which chokes on the non-subclass subclass. So just remove it for now

class _DelegatedAttribute:
    def __init__(self, delegator_name, attr_name, baseclass):
        self.attr_name = attr_name
        self.delegator_name = delegator_name
        self.baseclass = baseclass

    def __get__(self, instance, klass):
        if instance is None:
            # klass.DelegatedAttr() -> baseclass.attr
            return getattr(self.baseclass, self.attr_name)
        else:
            # instance.DelegatedAttr() -> instance.delegate.attr
            return getattr(self.delegator(instance), self.attr_name)

    def __set__(self, instance, value):
        # instance.delegate.attr = value
        setattr(self.delegator(instance), self.attr_name, value)

    def __delete__(self, instance):
        delattr(self.delegator(instance), self.attr_name)

    def delegator(self, instance):
        # minor syntactic sugar to help remove "getattr" spam (marginal utility)
        return getattr(instance, self.delegator_name)

    def __str__(self):
        return ""


def _custom_inherit(baseclass, delegator='delegate', include=None, exclude=None):
    '''A decorator to customize inheritance of the decorated class from the
    given baseclass. `delegator` is the name of the attribute on the subclass
    through which delegation is done;  `include` and `exclude` are a whitelist
    and blacklist of attrs to include from baseclass.__dict__, providing the
    main customization hooks.'''
    # `autoincl` is a boolean describing whether or not to include all of baseclass.__dict__

    # turn include and exclude into sets, if they aren't already
    if not isinstance(include, set):
        include = set(include) if include else set()
    if not isinstance(exclude, set):
        exclude = set(exclude) if exclude else set()

    # delegated_attrs = set(baseclass.__dict__.keys()) if autoincl else set()
    # Couldn't get the above line to work, because delegating __new__ fails miserably
    delegated_attrs = set()
    attributes = include | delegated_attrs - exclude

    def wrapper(subclass):
        ## create property for storing the delegate
        #setattr(subclass, delegator, None)
        # ^ Initializing the delegator is the duty of the subclass itself, this
        # decorator is only a tool to create attrs that go through it

        # don't bother adding attributes that the class already has
        attrs = attributes - set(subclass.__dict__.keys())
        # set all the attributes
        for attr in attrs:
            setattr(subclass, attr, _DelegatedAttribute(delegator, attr, baseclass))
        return subclass

    return wrapper

#
################################################################################
# Next, the other helper for _SequencesData: class wrapper around stdlib.heapq

import heapq as _heap
from functools import partial

class _Heap(list):

     def __init__(self, iterable=()):
          if iterable:
               super().__init__(iterable)
          else:
               super().__init__()

          self.push = partial(_heap.heappush, self)
          self.pop = partial(_heap.heappop, self)
          self.pushpop = partial(_heap.heappushpop, self)
          self.replace = partial(_heap.heapreplace, self)
          self.heapify = partial(_heap.heapify, self)

          self.heapify()

#
################################################################################
# Next, _SequencesData, the private class implementing the underlying dictionary
# and priority heap. For subclasses/external use, the dictionary is only directly
# accessible in an immutable fashion (though the public methods mutate it as
# necessary)

# Error raised if the file can't be locked
class LockError(Exception): pass


@_custom_inherit(dict, delegator='_data', include=['__len__', '__getitem__',
                   '__contains__', 'get', 'items', 'keys', 'values', '__str__'])
# TODO: types.MappingProxyType? Why is that buried away where it's useless?
class _SequencesData:
     '''The class that reads and writes The Sequence Data File. The `file`
     constructor argument is immutable for the lifetime of the object. Writing
     also writes to the other two files (which are read-only).'''

     def __init__(self, config):
          '''Create the object with its one and only jsonfile. To switch files,
          you must finalize this object and "manually" move the file, then make
          a new SequencesManager object.'''
          self._jsonfile = config['jsonfile']
          self._lockfile = config['lockfile']
          self._txtfile  = config['txtfile']
          # For priority purposes, we keep the jsonlist in minheap form ordered
          # by priority. The dict is an access convenience for most purposes.
          self._data = None # Will cause errors if you try and use this class
          self._heap = None # before actually reading data

     # See heap_impl_details.txt for a detailed rationale for the heap design.
     # The gist is we just use standard heap methods for everything; dropping
     # seqs nukes the relevant heap entry, so heap-read methods must error check
     # for valid entries

     @property
     def file(self):
          return self._jsonfile


     def _lock(self):
          try:
               open(self._lockfile, 'x').close()
          except FileExistsError:
               raise LockError("Lock file {} exists, _SequencesData uninitialized".format(self._lockfile)) from None
          self._have_lock = True


     def _unlock(self):
          self._have_lock = False
          rm(self._lockfile) # Should we test for problems or just let exceptions propgate?


     def _lock_init_empty(self):
          '''Use if starting from scratch, not reading from file'''
          self._lock()
          self._data = dict()
          self._heap = _Heap()


     def _read_init(self):
          with open(self.file, 'r') as f:
               data = json.load(f)

          tmpheap = data['aaData']
          if 'resdatetime' in data:
               self.resdatetime = data['resdatetime']

          self._data = dict()
          self._heap = _Heap([None])
          self._heap *= len(tmpheap)
          # Heap/list constructors copy their input, so multiply after constructor

          for i, dat in enumerate(tmpheap):
               ali = AliquotSequence(lst=dat)
               self._heap[i] = self._make_heap_entry(ali)
               self._data[ali.seq] = ali

          self._heap.heapify()


     def readonly_init(self):
          self._have_lock = False
          self._read_init()


     def lock_read_init(self):
          '''Initialize self from the (immutable attribute) `file` passed to the constructor.'''
          self._lock()
          _logger.info("Lock acquired, reading {}".format(self.file))
          try:
               self._read_init()
          except:
               self._unlock()
               raise


     @contextmanager
     def acquire_lock(self, block_minutes=0):
          '''Use this to begin a `with` statement'''
          # seems better to *not* define self as a context manager, I don't think
          # `self` will ever have a name suitable for reading a with statement,
          # i.e. "with seqinfo.acquire_lock():" is much clearer than "with seqinfo:"
          self._blocking_lock_read_init(block_minutes)
          try:
               yield # Exceptions in the body of `with` are reraised here
          finally: # Unhandled except to guarantee cleanup
               self.write_unlock()


     def _blocking_lock_read_init(self, block_minutes):
          # Thin wrapper around lock_read_init, only difference is artifical blocking
          seconds = block_minutes*60
          period = 5 # No idea if this is sane or not
          count = seconds // period

          try:
               self.lock_read_init()
          except LockError as e:
               f = e
               _logger.warning("Failed to acquire lock for {}, retrying in {} seconds".format(self.file, period))
          else:
               return
          # I've yet to see a good alternative to the missing do...while syntax that Python lacks
          for i in range(count):
               sleep(period)
               try:
                    self.lock_read_init()
               except LockError as e:
                    f = e # rebind the exception to the local scope
                    _logger.warning("Failed to acquire lock for {}, retrying in {} seconds".format(self.file, period))
               else:
                    return
          raise f


     def write(self):
          '''Finalize self to file. Totally overwrites old data with current data.'''
          if not self._have_lock: raise LockError("Can't use SequencesManager.write() without lock!")
          # TODO: should these errors be (programmatically) distinguishable from unable-to-acquire-lock errors?
          # ignore dropped seqs (HEAPENTRY)
          out = [item[2] for item in self._heap if (item[2] and item[2] in self._data)]
          # Find seqs that have been dropped from heap, they're just appended
          # at the end, no heapifying
          missing = set(self._data.keys()).difference(out)
          out = [self._data[seq] for seq in out]
          out.extend(self._data[seq] for seq in missing)
          # TODO: This is effectively cleaning the heap. Should we actually save the cleaned heap?
          # self._heap = _Heap(out) #(copies entire list)

          outdict = {"aaData": out}
          try:
               outdict['resdatetime'] = self.resdatetime
          except Exception:
               pass
          json_string = json.dumps(outdict, ensure_ascii=False, sort_keys=True).replace('],', '],\n') + '\n'
          # sort_keys to get reproducible output for testing, ensure_ascii=False to allow fancy names
          with open(self._jsonfile, 'w') as f:
               f.write(json_string)
          del json_string # Both outstrings generated here can be multiple megabytes each

          if self._txtfile:
               txt_string = ''.join(str(ali)+'\n' for ali in sorted(out, key=lambda ali: ali.seq) if ali.is_minimally_valid())
               # we want to go easy on newly added seqs with invalid data
               with open(self._txtfile, 'w') as f:
                    f.write(txt_string)
               del txt_string

          del out


     def write_unlock(self):
          try:
               self.write()
          except BaseException as e:
               _logger.exception(f"seqinfo failed to write!", exc_info=e)
               raise
          finally:
               self._unlock()
          _logger.info("seqinfo written, lock released")


     @staticmethod
     def _make_heap_entry(ali):
          # Must be sabotage-able, i.e. mutable, can't use tuple
          # All code that depends on the format here is tagged with HEAPENTRY
          entry = [ali.priority, ali.time, ali.seq]
          ali._heap_entry = entry # We need to track heap entries so we can sabotage them upon seqdrop
          return entry


     @staticmethod
     def _sabotage_heap_entry(ali):
          # HEAPENTRY
          ali._heap_entry[2] = None


     def pop_n_todo(self, n): # Should the two pop* methods be write-only?
          '''A lazy iterator yielding the n highest priority sequences'''
          while n > 0:
               seq = self._heap.pop()[2] # HEAPENTRY
               if seq: # heap entries are sabotaged by setting seq==0
                    n -= 1
                    yield seq


     def pop_seqs(self, seqs):
          '''Rather than popping the n most important seqs, instead pop the specified seqs'''
          for seq in seqs:
               self._sabotage_heap_entry(self._data[seq])


     def drop(self, seqs):
          '''Drop the given sequences from the dictionary.'''
          if not self._have_lock: raise LockError("Can't use SequencesManager.drop() without lock!")
          _logger.info("Dropping seqs {}".format(', '.join(str(s) for s in seqs)))
          # ^ I can't decide if this should be in the actual package or at clients' discretion
          for seq in seqs:
               if seq not in self._data:
                    _logger.warning("seq {} not in seqdata".format(seq))
                    continue
               ali = self._data[seq]
               self._sabotage_heap_entry(ali)
               del self._data[seq]
               del ali


     def push_new_info(self, ali):
          '''Call this method to insert a newly updated AliquotSequence object
          into the underlying datastructures. Any previous such object is
          silently overwritten.'''
          if not self._have_lock: raise LockError("Can't use SequencesManager.push_new_info() without lock!")
          if ali.seq in self._data:
               self._sabotage_heap_entry(self._data[ali.seq])
          self._data[ali.seq] = ali
          self._heap.push(self._make_heap_entry(ali))

#
#
################################################################################


################################################################################
# Finally, we get to the public class. It exposes the public methods of its
# parent (which are those that require direct access to the underlying
# datastructures) in addition to defining the common algorithms useful for scripts
# operating on the data which *don't* require special access. Since there are
# several such algorithms, they are separated out into this public class.

class SequencesManager(_SequencesData):
     '''The public class which implements the basic methods to manipulate
     aliquot sequence data, as well as several common algorithms on top of the
     basic methods. Update the resdatetime attribute when reservations are
     spidered.'''

     def find_merges(self):
          '''Returns a tuple of (mergee, (*mergers)) tuples (does not drop)'''
          ids = defaultdict(list)
          for ali in self.values():
               ids[ali.id].append(ali.seq)

          merges = [list(sorted(lst)) for lst in ids.values() if len(lst) > 1]
          merges = tuple((lst[0], lst[1:]) for lst in merges)
          if merges:
               # not really a warning, but noteworthy enough e.g. to trigger an email
               _logger.warning("Found merges!") # LOGGER.notable()
               for target, drops in merges:
                    _logger.warning('The seq(s) {} seem(s) to have merged with {}'.format(', '.join(str(d) for d in drops), target)) # LOGGER.notable()
          return merges


     def find_and_drop_merges(self):
          '''A convenience method wrapped around `find_merges` and `drop`.'''
          if not self._have_lock: raise LockError("Can't use SequencesManager.find_and_drop_merges() without lock!")
          merges = self.find_merges()
          drops = [drop for target, drops in merges for drop in drops]
          # I still say that "they" got the loop order wrong in comprehensions
          if drops:
               self.drop(drops)
          return merges


     def reserve_seqs(self, name, seqs):
          '''Mark the `seqs` as reserved by `name`.
          Returns (successes, DNEs, already_owns, other_owns)'''
          if not self._have_lock: raise LockError("Can't use SequencesManager.reserve_seqs() without lock!")
          success, DNEs, already_owns, other_owns = [], [], [], []
          for seq in seqs:
               if seq not in self:
                    DNEs.append(seq)
                    continue

               other = self[seq].res

               if not other:
                    self[seq].res = name
                    success.append(seq)
               elif name == other:
                    already_owns.append(seq)
               else:
                    other_owns.append((seq, other))

          if DNEs: _logger.warning("reserve_seqs ({}): seqs don't exist: {}".format(name, DNEs))
          if already_owns: _logger.warning("reserve_seqs ({}): seqs are already reserved: {}".format(name, already_owns))
          if other_owns: _logger.warning("reserve_seqs ({}): seqs are reserved by someone else: {}".format(name, other_owns))
          if success: _logger.info("reserve_seqs ({}): successfully added {}".format(name, success))

          return success, DNEs, already_owns, other_owns


     def unreserve_seqs(self, name, seqs):
          '''Mark the `seqs` as no longer reserved.
          Returns (successes, DNEs, not_reserveds, wrong_reserveds) '''
          if not self._have_lock: raise LockError("Can't use SequencesManager.unreserve_seqs() without lock!")
          success, DNEs, not_reserveds, wrong_reserveds = [], [], [], []
          for seq in seqs:
               if seq not in self:
                    DNEs.append(seq)
                    continue

               current = self[seq].res

               if not current:
                    not_reserveds.append(seq)
               elif name == current:
                    self[seq].res = ''
                    success.append(seq)
               else:
                    wrong_reserveds.append((seq, current))

          if DNEs: _logger.warning("unreserve_seqs ({}): seqs don't exist: {}".format(name, DNEs))
          if not_reserveds: _logger.warning("unreserve_seqs ({}): seqs are not currently reserved: {}".format(name, not_reserveds))
          if wrong_reserveds: _logger.warning("unreserve_seqs ({}): seqs aren't reserved by dropee: {}".format(name, wrong_reserveds))
          if success: _logger.info("unreserve_seqs ({}): successfully dropped {}".format(name, success))

          return success, DNEs, not_reserveds, wrong_reserveds


     def update_seqs(self, name, seqs):
          '''Validate sequences to be updated. (Caller is responsible for actual updating.)
          Returns (successes, DNEs) '''
          if not self._have_lock: raise LockError("Can't use SequencesManager.update_seqs() without lock!")
          success, DNEs = [], []
          for seq in seqs:
               if seq not in self:
                    DNEs.append(seq)
                    continue
               success.append(seq)

          if DNEs: _logger.warning("update_seqs ({}): seqs don't exist: {}".format(name, DNEs))
          if success: _logger.info("update_seqs ({}): successfully queued for update {}".format(name, success))

          return success, DNEs


     def calc_common_stats(self):
          sizes = Counter(); lens = Counter(); guides = Counter(); progs = Counter(); cofacts = Counter()
          totsiz = 0; totlen = 0; avginc = 0; totprog = 0; data_total = 0
          for ali in self.values():
               if not ali.is_minimally_valid():
                    continue
               sizes[ali.size] += 1; totsiz += ali.size
               lens[ali.index] += 1; totlen += ali.index
               guides[ali.guide] += 1; avginc += ali.index/ali.size
               progs[ali.progress] += 1
               cofacts[ali.cofactor] += 1

               if isinstance(ali.progress, int):
                    totprog += 1
               data_total += 1

          # Put stats table in json-able format
          lentable = []; lencount = 0
          sizetable = [ [key, value] for key, value in sizes.items() ]
          cofactable = [ [key, value] for key, value in cofacts.items() ]
          for leng, cnt in sorted(lens.items(), key=lambda tup: tup[0]):
               lentable.append( [leng, cnt, "{:2.2f}".format(lencount/(data_total-cnt)*100)] )
               lencount += cnt
          guidetable = [ [key, value] for key, value in guides.items() ]
          progtable = [ [key, value] for key, value in progs.items() ]

          # see allseq.py for use
          return sizetable, cofactable, guidetable, progtable, lentable, totlen/totsiz, avginc/data_total, totprog, totprog/data_total



