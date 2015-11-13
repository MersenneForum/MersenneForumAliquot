#! /usr/bin/env python3

import aliquot as aq
import numtheory as nt
from allseq import Sequence
import json, re
from myutils import blogotubes

# Some of the data handling code is copied from allseq.py
data_file = 'http://dubslow.tk/aliquot/AllSeq.json'

composite = re.compile(r' <a href="index.php\?id=([0-9]+?)"><font color="#002099">[0-9.]+?</font></a><sub>&lt;')
smallfact = re.compile(r' <a href="index.php\?id=[0-9]+?"><font color="#000000">([0-9^]+?)</font></a>')
largefact = re.compile(r' <a href="index.php\id=([0-9]+?)"><font color="#000000">[0-9]+?[.]{3}[0-9]{2}</font></a><sub>&lt;')
largenum = re.compile(r'<td align="center">(([0-9\s]|(<br>))+?)</td>')

if __name__ == "__main__" and 'http' in data_file:
     print("Getting the current data")
     txt = blogotubes(data_file)
     if txt is None:
          raise ValueError("Couldn't get data file")
     else:
          data_file = 'AllSeq.json'
          with open(data_file, 'w') as f:
               f.write(txt)

def read_data():
     with open(data_file, 'r') as f:
          data = json.load(f)['aaData']     
     return {seq[0]: Sequence(lst=seq) for seq in data}

def get_num(id):
     page = blogotubes('http://factordb.com/index.php?showid='+id)
     num = largenum.search(page).group(1)
     num = re.sub(r'[^0-9]', '', num)
     return int(num)

def get_id_info(id):
     base = 'http://factordb.com/index.php?id='
     page = blogotubes(base+str(id))
     if not page or 'FF' in page:
          return None
     smalls = smallfact.findall(page)
     largeids = largefact.findall(page)
     compid = composite.search(page).group(1)
     #print(compid, "\n{}\n##########################################\n\n{}".format(smalls, page))
     larges = list(map(get_num, largeids))
     comp = get_num(compid)
     return nt.Factors(' * '.join(smalls + larges)), comp

def examine_seq(seq):
     # We need a way to filter which sequences we query the FDB about.
     # For now, we can only handle driver*(even powered primes)*composite, so ignore all others.
     
     # Also, although this doesn't strictly match the previous criterion, the allseq.py script
     # truncates all primes greater than ~10 digits and assumes they have no exponent.
     # This assumption doesn't match the previous criterion but exceptions are very rare,
     # so we work off it and ignore sequences with a 'P' in them (and reserved sequences).
     if 'P' in seq.factors or seq.res:
          return None

     guide = nt.Factors(seq.guide)
     factors = nt.Factors(seq.factors)
     for prime in factors:
          if factors[prime] % 2 == 1 and prime not in guide: # The current filtering criterion
               return None
     # We only want to bother asking the FDB about actual drivers
     if not aq.is_driver(seq.guide):
          return None
     # Also check for class == 2...
     clsss = aq.get_class(nt.Factors(seq.factors))
     if clsss < 2:
          return None
     elif clsss > 2:
          if seq.guide != "2^3 * 3":
               print("Sequence {:>6} has a driver but also has class {}: {}".format(seq.seq, clsss, seq.factors))
          return None
     # Now we have sufficient reason to get details on this line
     #print("Getting detailed data for {}: {}".format(seq.seq, seq.factors))
     info = get_id_info(seq.id)
     if info is None:
          #print("Sequence {} is out of date (or invalid FDB response)".format(seq.seq))
          return None
     g = str(aq.get_guide(info[0], powers=False))
     if g != seq.guide:
          print("Sequence {} guide {} doesn't match data ({})".format(seq.seq, g, seq.guide))
          return None

     out = analyze(*info)
     if out:
          return info
     return None

def analyze(facts, composite):
     """Takes the known parts of the current step in the sequence, together with the
     remaining composite and determines if this step may break the driver (assuming
     the composite is a semi-prime).
     
     returns None on error (or raises an exception)
     returns False if the driver is guaranteed to remain
     returns True if the driver *may* break (determined by Clifford Stern's analysis)
     
     Currently the only focus is class 2 drivers (such as perfect numbers with an
     even power). Class 1 drivers can only be broken by large primes. Class 3 and
     greater TBD (help with describing the possible cases is appreciated)"""
     if not isinstance(facts, nt.Factors):
          raise TypeError("analyze() expects a numtheory.Factors instance for its first arg")

     guide = aq.get_guide(facts)
     cls = aq.get_class(guide=guide)
     
     if cls < 2:
          print("Class less than 2")
          return False
     if cls > 2:
          print("Class greater than 2")
          return None #raise ValueError("analyze() can't handle class 3 or greater yet")

     # http://dubslow.tk/aliquot/analysis.html
     # The requirement for a driver breaking ("mutation") is that "the 2s count of
     # t is equal to or less than the class of (2^a)*v", where 2^a*v is the guide,
     # and t is the set of prime factors with odd powers (and s is the primes with
     # even powers).
     s = nt.Factors()
     t = nt.Factors()
     for prime in facts:
          if prime not in guide:
               if facts[prime] % 2 == 0:
                    s[prime] = facts[prime]
               else:
                    t[prime] = facts[prime]

     # For class 2 guides/drivers, the semi-prime in question must be the only part of t
     if len(t.keys()) > 0:
          #print("Have a odd power prime cofactor: {}".format(t))
          return False
     # Finally, if t is a semi-prime, its constituents must each be == 1 (mod 4),
     # which implies that t must also be such (but the latter doesn't imply the
     # former, for of course t may also be two primes == 3 (mod 4)).
     return composite % 4 == 1

# The main function
def main():
     # This and other code in this and other modules is sometimes a bit confusing
     # because I use 'seq' for both just the integer of the sequence leader
     # *and* the corresponding Sequence object
     # data is a dictionary mapping the ints to the Sequence objects
     # `for seq in data` is iterating over the keys, so there seq is just an int
     data = read_data()
     targets = [data[seq] for seq in data if examine_seq(data[seq])]
     # OTOH targets is a list of the Sequence objects, so here seq is the object not the int
     targets.sort(key=lambda seq: seq.cofact)
     for seq in targets:
          print("{:>6} may have a driver that's ready to break (composite is 1 mod 4): {}".format(seq.seq, seq.factors))

if __name__ == "__main__":
     main()
