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

"""
This is module to do basic Aliquot sequence analysis as described by Clifford
Stern at <http://rechenkraft.net/aliquot/analysis.html>. This is version 2, with
a new PRP test and with the basic datatype moved to a different module.

Provided functions:
is_prime() -- deterministic trial division
prp() -- probabilistic miller-rabin test(s)
factor()
sigma()
aliquot() -- Equivalent to sigma(n) - n
get_guide()
get_class()
is_driver()
twos_count()

The main datatype of this module is (instances of) the Factors class. All of the 
functions are capable of taking a Factors() object as their argument; they are
also able to take an int or a literal string of factors. A string of factors is
a list of factors separated by '*', with optional powers marked by '^'. Such a 
valid string might be:
"2^3 * 3^2 * 5 * 7 * 31^5"
Whitespace doesn't matter.

The Factors class, factor() function and primality functions are provided in a 
different module; you can see the source for it at
<https://github.com/dubslow/MersenneForumAliquot/blob/master/numtheory/numtheory.py>.
In the future, I might look at adding Sage's abilities, or adding other
factoring/primality methods of my own design.

The important functionality of the module also comes from the Factors class, which 
is a subclass of dict(). The keys are the individual factors, and the corresponding
values are the power of that factor. Example:

>>> import aliquot as a
>>> num = a.Factors("2^3 * 3^2 * 5 * 7 * 31^5")
>>> num
{31: 5, 2: 3, 3: 2, 5: 1, 7: 1}

As demonstrated, the Factors() constructor can parse factor strings, but is also
capable of handling (small) integers or pre-initialized dictionaries of factors.
The reason to subclass dict() is to define custom versions of the str() and int()
functions that make sense in the integer factorization context, as well as to add
the factor string parsing. Example:

>>> num
{31: 5, 2: 3, 3: 2, 5: 1, 7: 1}
>>> str(num)
'2^3 * 3^2 * 5 * 7 * 31^5'
>>> print(num)
2^3 * 3^2 * 5 * 7 * 31^5
>>> int(num)
72145460520

Another example:

>>> num = a.Factors(72145460520)
>>> print(num)
2^3 * 3^2 * 5 * 7 * 31^5

factor() and get_guide() return Factors instances, while the other functions
return ints or booleans as appropriate.

More examples:

>>> print(num)
2^3 * 3^2 * 5 * 7 * 31^5
>>> a.get_guide(num)
{2: 3, 3: 2, 5: 1}
>>> print(a.get_guide(num))
2^3 * 3^2 * 5
>>> a.get_class(num)
2
>>> a.is_driver(a.get_guide(num))
True
>>> mun = a.aliquot(num)
>>> mun
204755687640
>>> mun = a.factor(mun)
>>> print(mun)
2^3 * 3^2 * 5 * 7 * 269 * 302053

>>> a.get_class('2^3*3*5')
0
>>> a.is_driver('2^2*3')
False
>>> a.get_class(2**2*7)
-1
>>> print(a.get_guide(4*49*5*13))
2^2 * 7^2
>>> print(a.get_guide(4*49*5*13, powers=False))
2^2 * 7
>>> a.get_class(4*49*5*13)
2
>>> a.get_class(4*49*5*13, powers=False)
-1

>>> a.factor(a.sigma(2**3))
{3: 1, 5: 1}
>>> print(_) # "_" is a special variable containing the previous result
3 * 5
>>> a.twos_count(_)
3
>>> 3 - _ # The power of 2 minus the twos_count of v=sigma(2**3) is the class
0
>>> a.get_class(2**3*3*5)
0
>>> a.get_class(2**3 * a.sigma(2**3))
0

>>> for b in range(1, 11):
...     v = a.factor(a.sigma(2**b))
...     guide = a.get_guide(2**b * int(v))
...     classs = a.get_class(guide)
...     print('a:', b, ' v:', v, ' guide:', guide, ' class:', classs)
... 
a: 1  v: 3  guide: 2 * 3  class: -1
a: 2  v: 7  guide: 2^2 * 7  class: -1
a: 3  v: 3 * 5  guide: 2^3 * 3 * 5  class: 0
a: 4  v: 31  guide: 2^4 * 31  class: -1
a: 5  v: 3^2 * 7  guide: 2^5 * 3^2 * 7  class: 2   # With just 3^1, the class is 0
a: 6  v: 127  guide: 2^6 * 127  class: -1
a: 7  v: 3 * 5 * 17  guide: 2^7 * 3 * 5 * 17  class: 3
a: 8  v: 7 * 73  guide: 2^8 * 7 * 73  class: 4
a: 9  v: 3 * 11 * 31  guide: 2^9 * 3 * 11 * 31  class: 0
a: 10  v: 23 * 89  guide: 2^10 * 23 * 89  class: 6
"""

from .numtheory import is_prime, prp, Factors, factor, _sanitize, sigma, quick_pow_of_two, _positive
from functools import lru_cache
from itertools import product as cartesian_product
     
def aliquot(n):
     n = _sanitize(n)
     return sigma(n) - int(n)

def get_guide(facts, powers=True):
     # powers: if false, '2 * 3^2 * 5' returns '2 * 3'; if true, returns '2 * 3^2'
     # "facts" is the factorization of n, which is allowed to contain extraneous factors
     facts = _sanitize(facts)
     if not isinstance(facts, Factors): facts = factor(facts)
     # Be sure it's properly factored

     pow_of_2 = facts[2]
     
     potential_guiders = factor(sigma(1 << pow_of_2))
     guide = Factors(); guide[2] = pow_of_2

     for guider in potential_guiders: # Construct v
          if guider in facts: # Figure out if "potential" is "actual"
               if powers:
                    guide[guider] = facts[guider]
               else:
                    guide[guider] = 1

     return guide

def canonical_form(n):
     '''Splits a number into its canonical aliquot form, i.e. (2^b*v)*s*t where 2^b*v
     is the guide, s is even powered primes, and t is everything else/odd powered primes.
     The return value is (n, guide, s, t) where each is a Factors instance'''
     n = _sanitize(n)
     if not isinstance(n, Factors): n = factor(n)

     guide = get_guide(n)
     s = Factors()
     t = Factors()
     rest_primes = set(n.keys()) - set(guide.keys())
     for p in rest_primes:
          a = n[p]
          if a & 1 == 1:
               t[p] = a
          else:
               s[p] = a

     if int(guide) * int(s) * int(t) != int(n):
          raise ValueError("Aliquot classification failed! Wtf?")
     return guide, s, t

def twos_count(t): # The power of two of sigma(t)
     t = _sanitize(t) # Check that n is a positive int
     if not isinstance(t, Factors): t = factor(t) # Factor n if not done already
     # http://www.rechenkraft.net/aliquot/intro-analysis.html#tauprimepowers
     odd_primes = set(t.keys()) - {2}
     tau = 0
     for p in odd_primes:
          a = t[p]
          if a & 1 == 1:
               tau += quick_pow_of_two(p+1) + quick_pow_of_two((a+1)>>1)
     return tau

beta = quick_pow_of_two
tau = twos_count

def get_class(n=0, guide=None, powers=True):
     if guide is None:
          guide = get_guide(n, powers)
     if powers:
          return guide[2] - twos_count(guide)
     else:
          v = guide.copy()
          del v[2]
          for p in v:
               v[p] = 1
          return guide[2] - twos_count(v)

def is_driver(n=0, guide=None):
     if guide is None:
          guide = get_guide(n, powers=False)
     return get_class(guide=guide, powers=False) <= 1

#def tau(p):
#     '''Indirectly calculates tau(p) by examining p mod powers of 2 (only works on odd primes)'''
#     # tau(p) == x <=> p === 2^x-1 (mod 2^(x+1))
#     # so
#     x = 1
#     two_to_x = 2
#     two_to_xp1 = 4
#     while p % two_to_xp1 != two_to_x - 1:
#          x += 1
#          two_to_x = two_to_x_1
#          two_to_xp1 <<= 1
#     return x

def mutation_possible(known_factors, composite, forms=None):
     '''Given an aliquot term in the form `known_factors` * `composite` (where the
     former is an `nt.Factors` instance), then test if a mutation is possible
     depending on how the composite factors. Returning an empty list guarantees
     that a mutation won't happen, but a non-empty list (which comprises the
     conditions on the component primes in the composite) does not guarantee that
     a mutation will occur.

     If `forms` is not passed, then the composite will be assumed to be either a
     semi-prime or a product of three primes (that is, `forms` == [(1,1), (1,1,1)] ).'''
     if forms is None:
          forms = [(1,1), (1,1,1)]
     target_tau = known_factors[2] - twos_count(known_factors)
     if target_tau < 2:
          return []
     forms = tuple(filter(lambda f: len(f) <= target_tau, forms)) # tau(n primes) >= n
     return [allowed_res for form in forms for allowed_res in composite_tau_lte(composite, target_tau, form)]

def composite_tau_lte(composite, x, form):
     '''This function is literally a one line list comprehension around test_composite_tau.
     
     Given an odd number n of unknown factorization, test if it's possible for tau(n)
     to be <= x, assuming in factors in the form given. A false retval guarantees 
     that tau(n) > x, but true does not guarantee that tau(n) <= x.

     `form` is a tuple-like object containing the prime powers that describe the
     hypothetical form of n. For instance to assume `n` is a semiprime, then pass
     `form = (1, 1)`; if n splits as three primes, then `form = (1, 1, 1)`, or if
     n is a prime multiplied by a prime cubed, then `form = (1, 3)` (or (3, 1) is
     equivalent). Given that tau(p^(2i)) = 0, even powers in the form will
     raise a value error.
     
     Returns a series of the congruence conditions which n may satisfy.'''
     return [pos_res for xprime in range(2, x+1) for pos_res in test_composite_tau(composite, xprime, form)]

def test_composite_tau(n, x, form):
     '''Given an odd number n of unknown factorization, test if it's possible for tau(n)
     to be x, assuming in factors in the form given. False guarantees that
     tau(n) != x, but true does not guarantee that tau(n) = x.

     `form` is a tuple-like object containing the prime powers that describe the
     hypothetical form of n. For instance to assume `n` is a semiprime, then pass
     `form = (1, 1)`; if n splits as three primes, then `form = (1, 1, 1)`, or if
     n is a prime multiplied by a prime cubed, then `form = (1, 3)` (or (3, 1) is
     equivalent). Given that tau(p^(2i)) = 0, even powers in the form will
     raise a value error.
     
     Returns a series of the congruence conditions which n may satisfy.'''

     n = int(_positive(n, "test_tau"))
     x = int(_positive(x-1, "test_tau"))+1
     # First, ignore the even part of n
     b = beta(n)
     n >>= b
     form = [int(power) for power in form]
     for power in form:
          if power & 1 != 1:
               raise ValueError("got an even prime power: {}".format(power))

     count = len(form)
     if count > x:
          return []
     form.sort()

     # As per the intro to sequence analysis page, tau(p^a) (a odd) = tau(p)
     # + beta((a+1)/2), while p^a === p mod any powers of 2 that matter, so for
     # the purposes of this analysis, just calculate the extra tau from higher
     # powers, subtract that from x, and then just proceed as if all primes are
     # power 1
     xtra = sum(beta((a+1)>>1) for a in form if a > 1) # The condition isn't necessary
     # But I think it's faster than "calculating" beta(1) a whole bunch
     x -= xtra
     if count > x:
          return []
     # Now for the given count, we create all possible combinations of `count` numbers
     # that sum to x
     combos = partitions_of_size(x, count)
     # Now we analyze each combo separately, and any possible matches are returned
     possible_residues = []
     for combo in combos:
          t = analyze_composite_tau(n, x, combo)
          if t:
               possible_residues.append(t)
     return possible_residues

def test_tau_to_str(result, comp_str='', sep=' '):
     return sep.join(analyze_tau_to_str(res, comp_str) for res in result)

composite_tau_lte_to_str = test_tau_to_str

def analyze_composite_tau(n, x, component_taus):
     '''Helper to test_composite_tau(). Given an odd number n and a target tau(n) together with
     a list of the specific tau(p) to be assumed for each prime in n, test if
     the implied conditions on p_i mod 2^{x_i+1} are compatible with n. If such a
     compatibility is possible, return it, else return an empty value.'''
     # First, ignore the even part of n
     b = beta(n)
     n >>= b
     # First we create the list of conditions on the component primes. We use the
     # criterion tau(p) = x <=> p == 2^x-1 (mod 2^(x+1))
     # We store the conditions as a list of (residue, modulus) conditions
     conditions = [((1<<x) - 1, 1<<(x+1)) for x in component_taus]
     # Now what we do is combine all the conditions modulo the largest modulus, which
     # we can do since the moduli are all multiples of each other.
     m = max(conditions, key=lambda cond: cond[1])[1]
     promoted_rs = []
     for ri, mi in conditions:
          q, r = divmod(m, mi)
          if r != 0:
               raise ValueError("Moduli don't divide! {} {}".format(m, mi))
          promoted_rs.append([(ri+i*mi) for i in range(q)])
     out = []
     actual_r = n % m
     # Now we take all possible combinations of the possible individual residues, making
     # sure to eliminate duplicate conditions (e.g. [1, 3, 5] mod 8 is the same as [3, 1, 5])
     # Now even after this de-duplication, some unique combos may have the same multiplied
     # residue mod m, e.g. [3, 5] and [1, 7] (mod 8), but they're still separate possibilities
     # on each constituent prime
     all_combos = {tuple(sorted(rs)) for rs in cartesian_product(*promoted_rs)}
     for rs in all_combos:
          r = 1
          for ri in rs:
               r = (r*ri)%m
          if r == actual_r:
               out.append(rs)
     if out:
          return out, actual_r, m, component_taus
     else:
          return []

def analyze_tau_to_str(result, comp_str=''):
     if not result:
          return
     out, r, m, comp_taus = result
     x = sum(comp_taus)
     xstr = '+'.join(str(x) for x in comp_taus)
     template = '''Assuming that {} is made of {} primes, then since it's {} (mod {}), it's possible that tau(n)={}={} via the following conditions: '''
     string = template.format(comp_str if comp_str else 'n', len(comp_taus), r, m, x, xstr)
     allconds_str = '; '.join(
          ', '.join('p{}%{}=={}'.format(i, m, ri) for i, ri in enumerate(rs, 1)) for rs in out
          )
     return string + allconds_str + '.'

@lru_cache()
def partitions_of_size(n, count):
     '''Creates all combinations of `count` numbers that sum to n (order doesn't
     matter, so combos are returned in sorted form)'''
     # Use a simple recursive construction with caching for performance.
     # A non-recursive construction certainly is not overly difficult
     if count < 1 or n < count:
          return set()
     if count == 1:
          return {(n,)}
     if n == count:
          return {(1,)*count}
     if n == count+1:
          return {(1,)*(count-1) + (2,)}

     combos = set()
     #print("making all sets n = {}, count = {}".format(n, count))
     for i in range(n-1, count-2, -1):
          news = partitions_of_size(i, count-1)
          for new in news:
               out = [n-i] + list(new)
               out.sort()
               out = tuple(out)
               #print("n = {}, i = {}, count = {}, new combo: {}".format(n, i, count, out))
               combos.add(out)
     return combos
