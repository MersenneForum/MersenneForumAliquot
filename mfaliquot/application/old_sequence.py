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
                    raise ValueError('AliquotSequence.__init__ received invalid size list (got {}, must be {})'.format(a, b))
               super().__init__(l)
               del kwargs['lst']
          else:
               super().__init__(self._defaults)

          for kw, val in kwargs.items():
               if kw not in self._map:
                    raise TypeError("unknown keyword arugment {}".format(kw))
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
          out = "{:>7d}  {:30s} {:>5d}  {:>3d}\n".format(self.seq, self.res, self.index, self.size)
          return out
