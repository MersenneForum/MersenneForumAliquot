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

from . import is_prime, prp, Factors, factor, _sanitize, sigma, quick_pow_of_two
     
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
     
     potential_guiders = factor(sigma(2**pow_of_2))
     guide = Factors(); guide[2] = pow_of_2

     for fact in potential_guiders: # Construct v
          if fact in facts: # Figure out if "potential" is "actual"
               if powers:
                    guide[fact] = facts[fact]
               else:
                    guide[fact] = 1

     return guide

def get_class(n=0, guide=None, powers=True):
     if guide is None:
          guide = get_guide(n, powers)
     v = Factors({key: powe for key, powe in guide.items() if key != 2 and powe > 0})
     return guide[2] - twos_count(v)

def is_driver(n=0, guide=None):
     if guide is None:
          guide = get_guide(n, powers=False)
     return get_class(guide=guide, False) <= 1

def twos_count(t): # The power of two of sigma(t)
     return quick_pow_of_two(sigma(t))

beta = quick_pow_of_two
tau = twos_count

#def tau(p):
#     '''Indirectly calculates tau(p) by examining p mod powers of 2 (only works on odd primes)'''
#     # tau(p) == x <=> p === 2^x-1 (mod 2^(x+1))
#     # so
#     x = 1
#     two_to_x = 2
#     two_to_x_1 = 4
#     while p % two_to_x_1 != two_to_x - 1:
#          x += 1
#          two_to_x = two_to_x_1
#          two_to_x_1 <<= 1
#     return x

def conditions_on_prime_if_tau_is_lte_x(x):
     ''' returns (residue, modulus) meaning any prime with tau <= x, then p
         must be `residue` mod `modulus`'''
     if x < 1: raise ValueError('x must be at least 1 (got {})'.format(x))
     # tau(p) = x <=> p+1 === 2^x mod 2^x+1
     # => p===-1 mod 2^x
     m = 1 << x
     return m - 1, m << 1


def probable_semiprime_tau(n, x):
     '''Tests if the semi prime of unknown composition n=pq could possibly
        have tau(n) = x. False guarantees tau != x, but True does not 
        guarantee tau = x.'''
     # tau(n) = tau(p) + tau(q) => tau(n) >= 2 right off the bat
     if x < 2: raise ValueError('x must be at least 2 (got {})'.format(x))
     possible_taus = [(y, x-y) for y in range(1, x//2+1)]
     allowable_residues = []
     for x1, x2 in possible_taus:
          r1, m1 = conditions_on_prime_if_tau_is_lte_x(x1)
          r2, m2 = conditions_on_prime_if_tau_is_lte_x(x2)
          # Now, by construction, x1 <= x2
          # And so m1 <= m2, and so m1 | m2 (and in fact m2//m1 is a power of two of course)
          if m2 % m1 != 0:
               raise ValueError("limitation moduli don't divide (should both be powers of 2): {}, {}".format(m1, m2))
          # Now we consider both primes mod m2, where we must "promote" the r1 residue to all its possible values
          # mod m2
          r1s = [(r1+i*m1) % m2 for i in range(m2//m1)]
          #print('x = {}, x1 = {}, x2 = {}, m2 = {}, r2 = {}, r1s = {}'.format(x, x1, x2, m2, r2, r1s))
          # For each possible r1 mod m2, the residue required is r1*r2, and see if n === r1*r2 (mod m2)
          for r1 in r1s:
               r = (r2*r1) % m2
               if n % m2 == r:
                    print("Given that n%{}={}, it's possible that p%{}={} and q%{}={}, meaning tau(p)={} and tau(q)={}, meaning tau(n) may yet be {}"
                         .format(m2, r, m2, r1, m2, r2, x1, x2, x))
                    allowable_residues.append((m2, (r1, r2)))
     return allowable_residues

def probable_semiprime_tau_lte_x(n, xprime):
     return [(x, allowed_residues) for x in range(2, xprime+1) for allowed_residues in probable_semiprime_tau(n, x)]
