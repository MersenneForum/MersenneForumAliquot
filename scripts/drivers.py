#!/opt/rh/rh-python36/root/usr/bin/python
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

# Some of the data handling code is copied from allseq.py
data_file = 'http://rechenkraft.net/aliquot/AllSeq.json'


###############################################################################

import json, re

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot.theory import numtheory as nt
from mfaliquot.theory import aliquot as aq
from mfaliquot.application import AliquotSequence, SequencesManager
from mfaliquot import blogotubes

# TODO: clean up this mess, ideally move some of it to mfaliquot.application.fdb

smallfact = re.compile(r' <a href="index.php\?id=[0-9]+?"><font color="#000000">([0-9^]+?)</font></a>')
largenums = r' <a href="index.php\?id=([0-9]+?)"><font color="{}">[0-9]+?[.]{{3}}[0-9]{{2}}(\^[0-9]*)?</font></a><sub>&lt;'
largefact = re.compile(largenums.format('#000000'))
composite = re.compile(largenums.format('#002099'))
#unknown = re.compile(largenums.format('#BB0000'))
#prp = re.compile(largenums.format('#550000'))
largedigits = re.compile(r'<td align="center">(([0-9\s]|(<br>))+?)</td>')

def get_data():
     global data_file
     if 'http' in data_file:
          print("Getting the current data")
          txt = blogotubes(data_file)
          if txt is None:
               raise ValueError("Couldn't get data file")
          else:
               data_file = 'AllSeq.json'
               with open(data_file, 'w') as f:
                    f.write(txt)


def get_num(id):
     page = blogotubes('http://factordb.com/index.php?showid='+id)
     num = largedigits.search(page).group(1)
     num = re.sub(r'[^0-9]', '', num)
     return num

def get_id_info(id):
     base = 'http://factordb.com/index.php?id='
     page = blogotubes(base+str(id))
     if not page:# or 'FF' in page:
          raise ValueError('http error')
     smalls = smallfact.findall(page)
     larges = largefact.findall(page)
     comps = composite.findall(page)
     #print(compid, "\n{}\n##########################################\n\n{}".format(smalls, page))
     # apply map(get_num, ...) to the first entry of the tuples, then concatenate the result with the second entry
     larges = [num+exp for num, exp in zip(map(get_num, (l[0] for l in larges)), (l[1] for l in larges))]
     comps = {int(num): (int(exp[1:]) if exp else 1) for num, exp in zip(map(get_num, (c[0] for c in comps)), (c[1] for c in comps))}
     #comp = get_num(compid)
     return nt.Factors(' * '.join(smalls + larges)), comps

def examine_seq(id, forms=None, n=None, guide=None, seq=None):
     '''Query the FDB by ID to analyze if the corresponding number may mutate by assuming
     the composite is of the given `forms`, where `forms` is a list of `form`s as used by
     the mfaliquot.aliquot.composite_tau_lte function. The optional n and guide arguments
     are for error checking purposes.'''
     primes, comps = get_id_info(id)
     if len(comps) == 0:
          return None # json data for this seq is out of date
     if len(comps) > 1 or list(comps.values()) != [1]:
          raise ValueError("Wtf?!? two composites or composite to a power? seq {}, id {}".format(seq.seq, seq.id))
     c = int(list(comps.keys())[0])
     guideprime, s, t = aq.canonical_form(primes)

     # We do a cross check that the fdb and data file agree: to do this,
     # we cut primes >9 digits from the fdb data
     nprime = {p: a for p, a in primes.items() if len(str(p)) <= 9}
     if (n is not None and nprime != n) or (guide is not None and guideprime != guide):
          #raise ValueError("Disagreement between local file and fdb: {} {}".format(n, nprime))
          print("Weird! Seq {} apparently is bad info in the data file.".format(seq.seq if seq else None))
          return None

     return aq.mutation_possible(primes, c, forms)

#count = 0
def filter_seq(seq):
     '''Examines unreserved sequences to see if they are prone to mutation. This
     currently ignores solely-power-of-2 guides with b > 3'''
     if seq.res:
          return None
     n = nt.Factors(seq.factors)
     guide, s, t = aq.canonical_form(n)
     seq.guide = guide
     # The target_tau for the composite is at most the class minus extant prime factor count
     cls = aq.get_class(guide=guide)
     num_larges = seq.factors.count('P')
     upper_bound_tau = cls - num_larges - len(t)

     if cls < 2 or upper_bound_tau < 2: # Cheap tests to eliminate almost all sequences
          return None

     # Next we ignore sequences whose guide is solely a power of 2 greater than 3
     v = nt.Factors({p: a for p, a in guide.items() if p != 2 and a > 0})
     if int(v) == 1 and cls > 3:
          return None
     # This condition greatly reduces fdb load, but excludes a lot of sequences
     if not aq.is_driver(guide=guide):
          return None

     return n, guide

# The main function
def main():
     #print('Getting data')
     #get_data()
     print('Starting examinations')
     # This and other code in this and other modules is sometimes a bit confusing
     # because I use 'seq' for both just the integer of the sequence leader *and*
     # the corresponding AliquotSequence object.
     # data is a dictionary mapping the ints to the AliquotSequence objects.
     data = SequencesManager('../website/html/AllSeq.json')
     data.readonly_init()
     targets = []; derp = []
     for i, seq in enumerate(data.values()):
          #print('looking at seq {}'.format(i))
          ress = filter_seq(seq)
          if ress:
               derp.append((seq, ress))
     print('Getting details for {} seqs'.format(len(derp)))
     for seq, ress in derp:
          res = examine_seq(seq.id, None, *ress, seq)
          if res:
               targets.append((seq, res))
     targets.sort(key=lambda tup: (not tup[0].driver, tup[0].klass, tup[0].cofactor)) # Drivers first, then sort by class first, secondary sort by comp size
     for seq, ress in targets:
          for res in ress:
               print("{:>6} ~ {} (class {}) maybe: {}".format(seq.seq, seq.guide, seq.klass, aq.analyze_composite_tau_to_str(res, 'C'+str(seq.cofactor))))

if __name__ == "__main__":
     main()
