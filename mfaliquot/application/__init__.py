# This is written to Python 3.3 standards
# indentation: 5 spaces (personal preference)


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
# contains the methods which manipulate its private data structures.
#
# SequencesManager subclasses _SequencesData, and implements the common algorithms
# which would be useful to scripts attempting to use the underlying data in the
# file. These algorithms needn't the private data, and for these two reasons is
# it a separate subclass, and also thus exportable.
#
################################################################################


import json


################################################################################
# First, the AliquotSequence class:

# A common class to multiple scripts. It uses a secret dictionary to map attributes
# to list form, which is handy for trivial JSONification. Perhaps not the best
# design, but the inexperienced me fresh to Python and OOP went power crazy with
# __getattribute__ and __setattr__, and I can certainly think of worse ways of
# doing this

class AliquotSequence(list):
     _map = {'seq':      (0, 0), # (list_index, default_val)
             'size':     (1, 0),
             'index':    (2, 0),
             'id':       (3, 0),
             'guide':    (4, None),
             'factors':  (5, None),
             'cofact':   (6, ''),
             'clas':     (7, None),
             'time':     (8, None),
             'progress': (9, 'Unknown'),
             'res':      (10, ''),
             'driver':   (11, '')
            }
     _defaults = [None] * len(_map)
     for attr, tup in _map.items():
          _defaults[tup[0]] = tup[1]

     def __setattr__(self, name, value): # Attributes are secretly just a specific slot on the list
          try:
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
                    raise ValueError('{}.__init__ received invalid size list (got {}, must be {})'.format(
                                      self.__class__.name, a, b))
               super().__init__(l)
          else:
               super().__init__(self._defaults)

          for kw, val in kwargs.items():
               # Silently toss unknown keys
               if kw in self._map:
                    self.__setattr__(kw, val)

     def is_valid(self):
          return self.seq and self.size > 0 and self.index > 0 and self.factors

     def __str__(self):
          if self.is_valid():
               return "{:>6d} {:>5d}. sz {:>3d} {:s}".format(self.seq, self.index, self.size, self.factors)
          else:
               raise ValueError('Not fully described! Seq: '+str(self.seq))

     def reservation_string(self):
          '''str(AliquotSequence) gives the AllSeq.txt format, this gives the MF reservations post format'''
          #   966  Paul Zimmermann   893  178
          #933436  unconnected     12448  168
          if not self.res:
               return ''
          out = "{:>6d}  {:30s} {:>5d}  {:>3d}\n".format(self.seq, self.res, self.index, self.size)
          if 'jacobs and' in self.res:
               out += '        Richard Guy\n'
          return out
          # TODO: extend allowable string lengths, remove special case

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


def custom_inherit(baseclass, delegator='delegate', include=None, exclude=None):
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

################################################################################
# Next, the other helper for _SequencesData: class wrapper around stdlib.heapq

import heapq as _heap
from functools import partial

class Heap(list):

     def __init__(self, iterable=None):
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


     def nsmallest(self, n, key=None):
          # heapq.nsmallest makes a *max* heap of the first n elements,
          # while we know that self is already a min heap, so we can
          # make the max heap construction faster
          self[:n] = reversed(self[:n])
          return _heap.nsmallest(n, self, key)


################################################################################
# Next, _SequencesData, the private class implementing the underlying dictionary
# and priority heap. For subclasses/external use, the dictionary is only accessible
# in an immutable fashion.


@custom_inherit(dict, delegator='_data', include=['__len__', '__getitem__',
                   '__contains__', 'get', 'items', 'keys', 'values', '__str__'])
class _SequencesData:
     '''The class that reads and writes The Sequence Data File. The `file`
     constructor argument is immutable for the lifetime of the object. Writing
     also writes to the other two files (which are read-only).'''

     def __init__(self, jsonfile, txtfile, resfile):
          '''Create the object with its one and only jsonfile. To switch files,
          you must finalize this object and "manually" move the file, then make
          a new SequenceData object.'''
          # For priority purposes, we keep the jsonlist in minheap form ordered
          # by priority. The dict is an access convenience for most purposes.
          self._jsonfile = jsonfile
          self._txtfile = txtfile
          self._resfile = resfile
          self._data = dict()
          self._heap = Heap()
     # Here's the intended dataflow design: The dict is the master list of data,
     # but the minheap/list is in charge of maintaining a (rough) heap order.
     # When written to file, the data from the dict (being the master) is
     # written, but in the order specified by the heap after that cycle's
     # updates and other modifications. It doesn't even really matter if some of
     # it isn't exactly a heap, because when reading, the data is used to
     # initialize the dict, then the list is *sorted*. Since it was written to
     # file in roughly a heap (and since the timsort used by Python is extremely
     # efficient at leveraging any partial order already present in data), this
     # initial sorting is nearly free. We then read the lowest N seqs off the
     # list as this cycle's todo, and do any further updates in the cycle using
     # the heap methods to maintain easy sortability with little cost. Then
     # write, rinse and repeat.
     # TODO: update the comment (no initial sorting)


     @property
     def file(self):
          return self._jsonfile


     def read_from_file(self):
          '''Initialize self from the immutable `file` passed to the constructor.'''
          with open(self.file, 'r') as f:
               heap = json.load(f)['aaData']
          self._heap = [None] * len(heap)
          for i, dat in enumerate(heap):
               ali = AliquotSequence(lst=dat)
               self._data[ali.seq] = ali
               self._heap[i] = self._heap_tuple(ali)

     @staticmethod
     def _heap_tuple(ali):
          return (ali.priority, ali.time, ali.seq)


     def get_N_todo(self, N):
          #from heapq import nsmallest
          # for N, reverse that sublist on the heap, beacuse nsmallest uses a maxheap
          # while our own list is already (nearly) a minheap, so reversing first N
          # will significantly speed up the maxheap
          return out


     def write_to_file(self):
          '''Finalize self to the given file. Totally overwrites it with data
          from self.'''

          # Find seqs that have been dropped from heap, they're just appended
          # at the end
          unsorted = set(self._data.keys()) - set(item[2] for item in self._heap)
          out = [self._data[item[2]] for item in self._heap] # heap ali object may be out of date
          out.extend(self._data[seq] for seq in unsorted)

          json_string = json.dumps({"aaData": out}).replace('],', '],\n') + '\n'
          txt_string = '\n'.join(str(ali) for ali in out) + '\n'
          res_string = '\n'.join(ali.reservation_string() for ali in out) + '\n'

          with open(self._jsonfile, 'w') as f:
               f.write(json_string)

          with open(self._txtfile, 'w') as f:
               f.write(txt_string)

          with open(self._resfile, 'w') as f:
               f.write(res_string)


     def drop(seqs):
          '''Drop the given sequences from the dictionary'''
          # TODO: determine how this interacts with the heap


class SequencesManager(_SequencesData):
     '''A class to do common algorithms on the seqsdata, but which should only
     use the public methods of its parent class (i.e. no manipulation of the
     underlying heap and dict). So separate them out here for conceptual
     clarity.'''

     def find_merges(self):
          ...

     def update_reservations(self):
          ...


