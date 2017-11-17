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

#class NoWildcardImports:
#     def __getitem__(self, index):
#          raise ImportError("{} is not wildcard importable!".format(__name__))
#__all__ = NoWildcardImports() # star imports are bad, mkay?


class SequenceData:
     '''The class that reads and writes The Sequence Data File. The `file`
     constructor argument is immutable for the lifetime of the object.'''

     def __init__(self, jsonfile, txtfile):
          '''Create the object with its one and only jsonfile. To switch files,
          you must finalize this object and "manually" move the file, then make
          a new SequenceData object.'''
          self._jsonfile = file
          self._txtfile = txtfile
          self._data = dict()


     @property
     def file(self):
          return self._jsonfile


     def read_from_file(self):
          '''Initialize self from the immutable `file` passed to the constructor.'''
          with open(self.file, 'r') as f:
               olddat = json.load(f)['aaData']
          for dat in olddat:
               ali = AliquotSequence(lst=dat)
               self._data[ali.seq] = ali


     def write_to_file(self):
          '''Finalize self to the given file. Totally overwrites it with data
          from self.'''
          ali_list = list(data_dict.values())
          ali_list.sort(key=lambda ali: ali.seq)
          # TODO: ali_list.sort(key=lambda ali: ali.priority)

          json_string = json.dumps({"aaData": ali_list}).replace('],', '],\n')+'\n'
          with open(self._file, 'w') as f:
               f.write(json_string)

          txt_string = '\n'.join(str(ali) for ali in ali_list)
          with open(self._txtfile, 'w') as f:
               f.write(txt_string+'\n')
