#! /usr/bin/env python3

# Some of the data handling code is copied from allseq.py
data_file = 'http://rechenkraft.net/aliquot/AllSeq.json'


###############################################################################

import json, re

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from numtheory import aliquot as aq
import numtheory as nt
from sequence import Sequence
from myutils import blogotubes


smallfact = re.compile(r' <a href="index.php\?id=[0-9]+?"><font color="#000000">([0-9^]+?)</font></a>')
largenums = r' <a href="index.php\?id=([0-9]+?)"><font color="{}">[0-9]+?[.]{{3}}[0-9]{{2}}(\^[0-9]*)?</font></a><sub>&lt;'
largefact = re.compile(largenums.format('#000000'))
composite = re.compile(largenums.format('#002099'))
#unknown = re.compile(largenums.format('#BB0000'))
#prp = re.compile(largenums.format('#550000'))
largedigits = re.compile(r'<td align="center">(([0-9\s]|(<br>))+?)</td>')

def read_data():
     with open(data_file, 'r') as f:
          data = json.load(f)['aaData']     
     return {seq[0]: Sequence(lst=seq) for seq in data}

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

count = 0
def examine_seq(seq):
     '''Examines unreserved sequences to see if they are prone to mutation. This
     currently ignores solely-power-of-2 guides with b > 3'''
     if seq.res:
          return None
     n, guide, s, t = aq.canonical_form(nt.Factors(seq.factors))
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
     # Now we query the fdb for the full numbers comprising the last term
     global count
     count += 1
     #print('getting data for sequence {:>6} = {:<30} take {}'.format(seq.seq, seq.factors, count))
     primes, comps = get_id_info(seq.id)
     if len(comps) == 0:
          return None # json data for this seq is out of date
     if len(comps) > 1 or list(comps.values()) != [1]:
          raise ValueError("Wtf?!? two composites or composite to a power? seq {}, id {}".format(seq.seq, seq.id))
     c = int(list(comps.keys())[0])
     nprime, guideprime, s, t = aq.canonical_form(primes)
     # We do a cross check that the fdb and data file agree: to do this,
     # we cut primes >9 digits from the fdb data
     tmp = [p for p in nprime if len(str(p)) >= 10]
     for p in tmp:
          del nprime[p]
     if nprime != n or guideprime != guide:
          #raise ValueError("Disagreement between local file and fdb: {} {}".format(n, nprime))
          print("Weird! Seq {} apparently is bad data on the website.".format(seq.seq))
          return None
     # Now we do one last tau check
     target_tau = cls - aq.twos_count(t)
     if target_tau < 2:
          return None
     #print("Seq {} checking composite".format(seq.seq))
     # For now, we only try the composite as a semi prime, though a decent number of the extant
     # composites haven't been ECMd, making 3 or more primes not implausible
     out = []
     res = aq.possible_mutation(c, target_tau, [1,1])
     if res:
          out.append(res)
     if target_tau > 2:
          # Test triple prime forms as well
          res = aq.possible_mutation(c, target_tau, [1,1,1])
          if res:
               out.append(res)
     return out


# The main function
def main():
     # This and other code in this and other modules is sometimes a bit confusing
     # because I use 'seq' for both just the integer of the sequence leader *and*
     # the corresponding Sequence object.
     # data is a dictionary mapping the ints to the Sequence objects.
     data = read_data()
     targets = []
     for i, seq in enumerate(data.values()):
          #print('looking at seq {}'.format(i))
          ress = examine_seq(seq)
          if ress:
               targets.append((seq, ress))
     targets.sort(key=lambda tup: (not tup[0].driver, tup[0].clas, tup[0].cofact)) # Drivers first, then sort by class first, secondary sort by comp size
     for seq, ress in targets:
          for res in ress:
               print("{:>6} with guide {} (class {}) may mutate: {}".format(seq.seq, seq.guide, seq.clas, aq.possible_mutation_to_str(res, 'C'+str(seq.cofact))))

if __name__ == "__main__":
     if 'http' in data_file:
          print("Getting the current data")
          txt = blogotubes(data_file)
          if txt is None:
               raise ValueError("Couldn't get data file")
          else:
               data_file = 'AllSeq.json'
               with open(data_file, 'w') as f:
                    f.write(txt)
     print('Starting examinations')
     main()
