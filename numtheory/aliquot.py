#! /usr/bin/python3
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

from . import is_prime, prp, Factors, factor, _sanitize, sigma, quick_pow_of_two, _positive
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
     return n, guide, s, t

def twos_count(t): # The power of two of sigma(t)
     t = _sanitize(t) # Check that n is a positive int
     if not isinstance(t, Factors): t = factor(t) # Factor n if not done already
     # http://www.rechenkraft.net/aliquot/intro-analysis.html#tauprimepowers
     tau = 0
     for p in t:
          a = t[p]
          if a & 1 == 1:
               tau += quick_pow_of_two(p+1) + quick_pow_of_two((a+1)>>1)
     return tau

beta = quick_pow_of_two
tau = twos_count

def get_class(n=0, guide=None, powers=True):
     if guide is None:
          guide = get_guide(n, powers)
     v = Factors({key: powe for key, powe in guide.items() if key != 2 and powe > 0})
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

def possible_mutation(composite, x, form):
     '''This function is literally a one line list comprehension around test_tau.
     
     Given a number n of unknown factorization, test if it's possible for tau(n)
     to be <= x, assuming in factors in the form given. A false retval guarantees 
     that tau(n) > x, but true does not guarantee that tau(n) <= x.

     `form` is a tuple-like object containing the prime powers that describe the
     hypothetical form of n. For instance to assume `n` is a semiprime, then pass
     `form = (1, 1)`; if n splits as three primes, then `form = (1, 1, 1)`, or if
     n is a prime multiplied by a prime cubed, then `form = (1, 3)` (or (3, 1) is
     equivalent). Given that tau(p^(2i)) = 0, even powers in the form will
     raise a value error.
     
     Returns a series of the congruence conditions which n may satisfy.'''
     return [pos_res for i in range(2, x+1) for pos_res in test_tau(composite, i, form)]

def test_tau(n, x, form):
     '''Given a number n of unknown factorization, test if it's possible for tau(n)
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
     # But I think it's faster than doing calculating beta(1) a whole bunch
     x -= xtra
     if count > x:
          return []
     # Now for the given count, we create all possible combinations of `count` numbers
     # that sum to x
     combos = partitions_of_size(x, count)
     # Now we analyze each combo separately, and any possible matches are returned
     possible_residues = []
     for combo in combos:
          t = analyze_tau(n, x, combo)
          if t:
               possible_residues.append(t)
     return possible_residues

def analyze_tau(n, x, component_taus):
     '''Helper to test_tau(). Given a number n and a target tau(n) together with
     a list of the specific tau(p) to be assumed for each prime in n, test if
     the implied conditions on p_i mod x_i+1 are compatible with n. If such a
     compatibility is possible, return it, else return an empty value.'''
     # First we create the list of conditions on the component primes. We use the
     # criterion tau(p) = x <-> p == 2^x-1 (mod 2^(x+1))
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
          promoted_rs.append([(ri+i*mi)%m for i in range(q)])
          # The modulo here isn't strictly necessary but it makes me feel better
     for rs in cartesian_product(*promoted_rs):
          r = 1
          for ri in rs:
               r = (r*ri)%m
          if n % m == r:
               conds_str = ', '.join('p{}%{}=={}'.format(i, m, ri) for i, ri in enumerate(rs))
               print(("Given that n%{}=={}, it's possible that the following conditionals hold: {}"+
                     ", which means that n may have twos count {}={}").format(
                     m, r, conds_str, x, '+'.join(str(x) for x in component_taus)))
               return rs, r, m
     return ()

@lru_cache(1<<10)
def partitions_of_size(n, count):
     '''Creates all combinations of `count` numbers that sum to n (order doesn't
     matter, so combos are returned in sorted form)'''
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
     for i in range(1, n-1):
          news = partitions_of_size(n-i, count-1)
          for new in news:
               out = [i] + list(new)
               out.sort()
               out = tuple(out)
               #print("n = {}, i = {}, count = {}, new combo: {}".format(n, i, count, out))
               combos.add(out)
     return combos
