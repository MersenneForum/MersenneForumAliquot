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

'''This is the common module for reading or writing to The Sequence Data
File.'''


from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
from myutils import custom_inherit
from sequence import AliquotSequence

#from ..myutils import custom_inherit
#from .sequence import AliquotSequence
import json
#from .heap import Heap


################################################################################


@custom_inherit(dict, delegator='_data', include=['__len__', '__getitem__',
                   '__contains__', 'get', 'items', 'keys', 'values', '__str__'])
class SequencesData:
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
          #self._heap = Heap()
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
               #self._heap[i] = (ali.priority, ali.time, ali.seq)


     def get_N_todo(self, N):
          out, self._heap = self._heap[:N], self._heap[N:]
          return out


     def write_to_file(self):
          '''Finalize self to the given file. Totally overwrites it with data
          from self.'''

          return

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

