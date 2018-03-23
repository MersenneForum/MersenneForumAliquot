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

from ..theory import aliquot as alq
from time import strftime, gmtime
from datetime import datetime, timedelta, date
DATETIMEFMT = '%Y-%m-%d %H:%M:%S'

# SequenceInfo is the standard record of information for one single sequence,
# and is the primary ingredient in the AllSeq.json/.html files. It is a dependency
# of several other files in the package. It uses a secret dictionary to map
# attributes to list form, which is handy for trivial JSONification. Perhaps not
# the best design, but the inexperienced me fresh to Python and OOP went power
# crazy with __getattribute__ and __setattr__, and I can certainly think of worse
# ways of doing this. Kept in a separate file for modularity and replacement
# purposes

class SequenceInfo(list):
     _map = {'seq':       (0,  None), # (list_index, default_val)
             'size':      (1,  None),
             'index':     (2,  None),
             'guide':     (3,  ''),
             'klass':     (4,  None),
             'abundance': (5,  None),
             'cofactor':  (6,  0),
             'factors':   (7,  ''),
             'res':       (8,  ''),
             'progress':  (9,  None),
             'time':      (10, ''),
             'priority':  (11, -1),
             'id':        (12, None),
             'driver':    (13, None)
            }
     _defaults = [None] * len(_map) # when dicts are guaranteed ordered, this could be simplified
     for attr, tup in _map.items():
          _defaults[tup[0]] = tup[1]


     def __setattr__(self, name, value):
          try:
               # Attributes are secretly just a specific slot on the list
               self[SequenceInfo._map[name][0]] = value
          except KeyError:
               super().__setattr__(name, value)


     def __getattribute__(self, name):
          try:
               return self[SequenceInfo._map[name][0]]
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
                    raise ValueError('SequenceInfo.__init__ received invalid size list (got {}, must be {})'.format(a, b))
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
          '''str(SequenceInfo) gives the AllSeq.txt format, this gives the MF reservations post format'''
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
          'small_cofactor_bound': 98, # inclusive
          'small_cofactor_discount': 1/150, # actually cofactor/discount. Must be less than 1/bound
          'downdriver_discount': 1/2,
          'shortterm_penalty_duration': 3, # days below which to apply a penalty
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

          if self.cofactor and self.cofactor <= config['small_cofactor_bound']:
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


     def process_no_progress(self, partial=False):

          if partial:
               self.progress = 0
          elif isinstance(self.progress, int):
               if self.progress > 0:
                    self.progress = id_created(self.id)
               elif self.progress == 0:
                    # TODO: is using last-update-time even any better than just the line-creation-date?
                    # would it be better still to bother with code to get the *cofactor* creation date??
                    self.progress = self.time.split()[0] # split() on whitespace between date and time
               else:
                    raise RuntimeError("wtf? negative progress in no_progress?? this should never happen")

          self.time = strftime(DATETIMEFMT, gmtime())
          self.calculate_priority()


     def process_progress(self, old, broken_offset=None):

          self.res = old.res
          self.progress = self.index - old.index
          self.guide, self.klass, self.driver = self.guide_description()
          self.set_abundance()

          if broken_offset:
               self.seq = old.seq
               self.index += broken_offset
               self.progress += broken_offset

          if self.progress <= 0:
               _logger.info(f"fresh sequence query of {self.seq} revealed no progress")
               self.progress = id_created(self.id)

          self.calculate_priority()


     def guide_description(self):
          """Returns a tuple of (str_of_guide, class_with_powers, is_driver)"""
          guide = alq.get_guide(self.factors, powers=False) # dr is an instance of "Factors"
          guidestring = str(guide) # str specified by "Factors" class
          if guidestring == '2':
               return "Downdriver!", 1, False
          else:
               return guidestring, alq.get_class(self.factors), alq.is_driver(guide=guide)


     def set_abundance(self):
          self.abundance = alq.abundance(self.factors)



from .fdb import id_created # circular import warning! how this worked before I'll never know

