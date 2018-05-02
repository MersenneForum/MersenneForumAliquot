#! /usr/bin/env python3

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


# This is a standalone script that uses yafu to generate lists of open aliquot
# sequences from first principles: start with all even numbers, take all seqs
# up to a certain bound, then eliminate all duplicates.

from subprocess import run, PIPE, STDOUT
import re
_PATTERN = re.compile(r'^P([0-9]+) = ([0-9]+)')
from mfaliquot.theory import numtheory as nt, aliquot as aq
#nt.set_cache(10**7)
from collections import defaultdict


################################################################################


def aliquot_sieve(bound, inputs=None):
     '''Calculate aliquot sequences and find mergers up to size `bound`.
     If inputs is None, all even numbers up to 10**7 are used. Otherwise,
     inputs should be a sequence of (original_seq, current_val) tuples for
     use in resuming/extending previous sieves to a higher bound.'''

     if inputs is None:
          values = defaultdict(list)
          unique = []
          l = 0
          for seq in range(2, 2*10**6, 2):
               #print(seq)
               n = seq
               #n = yafu_factor(n)
               n = nt.factor(n)
               m = aq.aliquot(n)
               if m < int(n):
                    continue
               n = m
               while n < 10**13:
                    #print(f"seq: {seq} -- val: {n} -- total vals: {len(values)}")
                    #n = yafu_factor(n)
                    m = nt.factor(n)
                    #if m._unparse() != n: raise ValueError("bad factors")
                    m = aq.aliquot(m)
                    if m in values:
                         break
                    if m <= 1:
                         break
                    values[m].append(seq)
                    n = m
               else:
                    unique.append(seq)
                    l += 1
                    if l % 1000 == 0:
                         print(f"have {l} unique seqs (ratio {seq/(2*l):2.2f}) removed per unique")
          return unique, values



def yafu_factor(n):
     # some sort of bug??? in yafu doesn't print small factors. fortunately,
     # mfaliquot.theory.numtheory gives a simple workaround
     factors = nt.Factors()
     _n = n # save for verification


     for p in nt._primes:
          while n % p == 0:
               factors[p] += 1
               n //= p
     if n == 1:
          return factors
     if n < 1:
          raise ValueError("wtf?")


     args = ['/home/bill/yafu/yafu', f'factor({n})', '-threads', '8']
     result = run(args, stdout=PIPE, stderr=STDOUT, universal_newlines=True)

     for line in result.stdout.splitlines():
          if line and line[0] == 'P':
               match = _PATTERN.match(line)
               if match:
                    factors[int(match.group(2))] += 1

     if not factors.full:
          raise ValueError("composite factor!")
     if int(factors) != int(_n):
          raise ValueError(f"bad factors: {_n}, {factors}")
     return factors


if __name__ == '__main__':
     print(yafu_factor(1892736541092853734567345636191985016290354645634563123418764325356735))
