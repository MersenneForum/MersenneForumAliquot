# This is written to Python 3.3 standards (may use 3.4 features, I haven't kept track)
# Note: tab depth is 5, as a personal preference


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

# A common class to multiple scripts. It uses a secret dictionary to map attributes
# to list form, which is handy for trivial JSONification. Perhaps not the best
# design, but the inexperienced me fresh to Python and OOP went power crazy with
# __getattribute__ and __setattr__, and I can certainly think of worse ways of
# doing this

class Sequence(list):
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
               self[self._map[name][0]] = value
          except KeyError:
               super().__setattr__(name, value)
     
     def __getattribute__(self, name):
          try:
               return self[Sequence._map[name][0]]
          except KeyError:
               return super().__getattribute__(name)
     
     def __init__(self, **kwargs):
          '''This recognizes all valid attributes, as well as the 'lst' kwarg
          to convert from list format (must be correct length).'''
          # Not exactly the prettiest code, but it's very general code
          # First super().__init__ as appropriate
          if kwargs.get('lst') is not None:
               l = kwargs['lst']
               a = len(l)
               b = len(self._map)
               if a != b:
                    raise ValueError('{}.__init__ received invalid size list (got {}, must be {})'.format(
                                      self.__class__.name, a, b))
               super().__init__(l)
          else:
               super().__init__(self._defaults)
          # Toss unknown keys
          for kw, val in kwargs.items():
               if kw in self._map:
                    self.__setattr__(kw, val)               

     def well_formed(self):
          return self.seq and self.size and self.index and self.factors
     
     def __str__(self):
          if self.well_formed():
               return "{:>6d} {:>5d}. sz {:>3d} {:s}\n".format(self.seq, self.index, self.size, self.factors)
          else:
               raise ValueError('Not fully described! Seq: '+str(self.seq))

     def reservation_string(self):
          '''str(Sequence) gives the AllSeq.txt format, this gives the MF reservations post format'''
          #   966  Paul Zimmermann   893  178
          #933436  unconnected     12448  168
          if not self.res:
               return ''
          out = "{:>6d}  {:15s} {:>5d}  {:>3d}\n".format(self.seq, self.res, self.index, self.size)
          if 'jacobs and' in self.res:
               out += '        Richard Guy\n'
          return out
