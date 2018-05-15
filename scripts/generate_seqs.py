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


import re, pickle
_PATTERN = re.compile(r'^P[0-9]+ = ([0-9]+)\r?$', re.MULTILINE)
from pexpect.replwrap import REPLWrapper
from pexpect.exceptions import TIMEOUT
from mfaliquot.theory import numtheory as nt, aliquot as aq
from collections import defaultdict
from os import remove


################################################################################


def aliquot_sieve(bound, inputs=None):
     '''Calculate aliquot sequences and find mergers up to size `bound`.
     If inputs is None, all even numbers up to 10**7 are used. Otherwise,
     inputs should be a sequence of (original_seq, current_val) tuples for
     use in resuming/extending previous sieves to a higher bound.'''

     yafu = Yafu('/home/bill/yafu/yafu -threads 8')

     if inputs is None:
          values = defaultdict(list)
          unique = []
          l = 0
          for seq in range(2, 5*10**6, 2):
               #print(seq)
               n = seq
               n = yafu.factor(n)
               #n = nt.factor(n)
               m = aq.aliquot(n)
               if m < int(n):
                    continue
               n = m
               while n < bound:
                    #print(f"seq: {seq} -- val: {n} -- total vals: {len(values)}")
                    m = yafu.factor(n)
                    #m = nt.factor(n)
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
                    if l % 100 == 0:
                         print(f"have {l} unique seqs (ratio {seq/l:2.2f} removed per unique)")
                    #print(f"have {l} unique seqs (ratio {seq/(2*l):2.2f} removed per unique)")
          return unique, values


class Yafu(REPLWrapper):

     def __init__(self, cmd, **kwargs):
          super().__init__(cmd, '>> ', None, **kwargs)
          self.child.delaybeforesend = None
          self.args = cmd, kwargs


     def factor(self, n):
          #_n = n # save for verification
          output = None
          while not output:
               try:
                    output = self.run_command(f"factor({n})", timeout=5)
               except TIMEOUT:
                    print(f'doh! {n}')
                    try:
                         remove('siqs.dat')
                         remove('factor.log')
                    except FileNotFoundError:
                         pass
                    self.__init__(self.args[0], **self.args[1])

          facts = nt.Factors()
          for factor in _PATTERN.findall(output):
               facts[int(factor)] += 1
          #if int(facts) != int(_n):
          #     raise ValueError(f"bad factors: {_n}, {facts}")
          return facts


if __name__ == '__main__':
     unique, values = aliquot_sieve(10**40)

     print(len(unique), len(values))

     with open('generate_seqs.values', 'wb') as f:
          pickle.dump(values, f, protocol=-1)

     with open('generate_seqs.txt', 'w') as f:
          for seq in unique:
               f.write(str(seq)+'\n')

     #print(Yafu('/home/bill/yafu/yafu -threads 8').factor(1892736541092853734567345636191985016290354645634563123418764325356735))
