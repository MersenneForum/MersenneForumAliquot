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
This is a module I've slowly built up as my number theory class progresses, with
some factoring functionality moved here from the aliquot.py module used for my
Aliquot sequences webpage. The aliquot.py module is here:
<https://github.com/dubslow/MersenneForumAliquot/blob/master/numtheory/aliquot.py>
"""

class Factors(dict):
     def __init__(self, facts=None):
          if facts is None:
               super().__init__()
          elif isinstance(facts, int):
               super().__init__()
               self = factor(facts, self)
               self.num = facts               
          elif isinstance(facts, str):
               super().__init__()
               try:
                    num = int(facts)
               except ValueError:
                    self._parse(facts)
               else:
                    self = factor(num, self)
                    self.num = num
          else:
               try:
                    super().__init__(facts)
               except:
                    raise TypeError('Argument must be a string, int, or mappable')
          self.full = True # True if fully factored, false if a composite remains

     def __missing__(self, key):
          return 0

     def _parse(self, string):
          if '·' in string:
               facts = [fact.strip() for fact in string.split('·')]
          else:
               facts = [fact.strip() for fact in string.split('*')]
          for fact in facts:
               try:
                    fact, power = fact.split('^')
               except ValueError:
                    power = 1
               try: 
                    fact = int(fact)
               except ValueError: pass
               else:
                    prime = is_prime(fact, _depth)
                    if prime == False or (prime is None and not prp(fact)): # Cheap error check
                         print("Warning: {} isn't prime!".format(fact))
                         self.full = False
                    self[fact] = int(power)
          self._unparse()
     
     def _unparse(self):
          num = 1
          for fact in self.keys():
               num *= fact**self[fact]
          self.num = num
          return num
     
     def int(self, recalc=False):
          if not recalc:
               try:
                    return self.num
               except AttributeError as e:
                    pass               
          return self._unparse()
     
     def __int__(self):
          return self.int()
     
     def keys(self):
          return sorted(super().keys()) # Lose viewing capability

     def values(self):
          return [self[key] for key in self.keys()] # Lose viewing capability

     def items(self):
          return [ (key, self[key]) for key in self.keys()] # Lose viewing capability

     def str(self, sep=' * '):
          def power_str(f, key):
               if f[key] > 1:
                    return '{}^{}'.format(key, f[key])
               else:
                    return str(key)

          facts = [key for key in self.keys() if self[key] > 0]
          if len(facts) == 0:
               return '1'
          else:
               return sep.join(power_str(self, key) for key in facts)
     
     def __str__(self):
          return self.str()

     def __repr__(self):
          return '{' + ', '.join(['{}: {}'.format(k,v) for k,v in self.items()]) + '}'

def _sanitize(arg):
     if isinstance(arg, dict):
          if isinstance(arg, Factors):
               return arg
          else:
               return Factors(arg)
     if isinstance(arg, int):
          return arg
     if isinstance(arg, str):
          try:
               return int(arg)
          except ValueError:
               return Factors(arg)
     raise TypeError('Expecting a str, int, or dict')

from math import sqrt as sr # Used in factor()/is_prime()
from itertools import compress

def primes(depth=10**6):
     # /u/Veedrac had the great ideas to change inner loop to slice assignment, 
     # and to not append to the list of primes while looping
     # http://www.reddit.com/r/Python/comments/20x61y/share_the_code_youre_most_proud_of/cg7umpa
     #print("Precalcing primes")
     if depth % 2 == 0: depth -= 1 # make depth odd
     if depth <= 1: return []
     length = depth // 2
     sieve = [True] * length # 3, 5, 7, etc. might be prime
     
     # i is the index, n = number = 2*i + 3
     # j = index of n^2 = (n^2-3)/2 = ((2i+3)^2-3)/2 = 2i^2 + 6i + 3
     # if i+=1, then j+=4i+8 (by 2(i+1)^2 + 6(i+1) - 2i^2 - 6i)
     i, j, step = 0, 3, 3 # Start with 3 and 3^2==9 (step explained below)
     while j < length:
          if sieve[i]: # then n is prime
               # Wrap the loop into a slice assignment
               # Start sieving from n^2 because smaller multiples would be eliminated earlier
               # so sieve[j] is False, and then n^2+2n is also false (n^2+n is automatically composite)
               # A jump of 2n numbers is a jump of n indices, so step = n = 2i + 3
               # Number of items changed = slice size // step + 1 if not perfect fit
               # Using -(-a // b) to round upwards
               sieve[j::step] = [False] * -(-(length-j) // step)
          
          j += 4*i + 8
          i += 1
          step += 2
          
     # translate sieve to primes
     primes = list(compress(range(3, depth+1, 2), sieve)) # itertools.compress filters one list by another
     primes.insert(0, 2)
     return primes

def set_cache(depth=10**6):
     global _depth, _primes, _count
     _depth = depth
     _primes = primes(depth)
     _count = len(_primes)

set_cache(10**5)

def _positive(n, func):
     try:
          out = int(n)
          if out <= 0:
               raise ValueError
     except ValueError:
          raise ValueError("{}() expects a positive integer!".format(func))
     return n

def quick_pow_of_two(n):
     if n == 0: return 0
     n = _positive(n, 'quick_pow_of_two')
     # To count the trailing zero bits (i.e. power of 2), first subtract one, then xor
     # The former takes xxxx1000 to xxxx0111, and xor will leave (ans+1) bits set to 1
     # Put another way, writing n=2^a * v, v odd, then n ^ (n-1) = 2^(a+1) - 1 (no matter v)
     out = (n ^ (n-1)) >> 1
     return out.bit_length()

def factor(num, depth=0, factors=None, start=3):
     num = _positive(num, "factor")

     if factors is None:
          factors = Factors()
          factors.num = num

     if _depth > depth > 1 : depth = _depth

     if num == 1:
          if not factors.full:
               print("Warning: there is a composite cofactor!")
          return factors

     if num & 1 == 0:
          factors[2] = quick_pow_of_two(num)
          return factor(num>>factors[2], depth, factors, start)

     try:
          sqrt = int(sr(num)) + 1
     except OverflowError:
          # If we're dealing with number larger than 1024 bits, we can't use
          # the math module to get the square root; instead, look for small
          # factors only if depth was set, else re-barf.
          if depth > 1:
               sqrt = depth + 1 # Code below checks that sqrt > depth
          else:
               raise OverflowError('num is too big for math.sqrt() to handle. '+
                    'If you still want to look for small factors, set the depth.')
     
     if start < _depth:
          ind = _primes.index(next_prime(start))
     else:
          ind = _count # == len(_primes)

     # First div with known primes
     for p in _primes[ind:]:
          if p > sqrt: # Then num is prime
               factors[num] += 1
               return factors
          if num % p == 0:
               factors[p] += 1
               return factor(num//p, depth, factors, p) # Restart sieving at p

     # Beyond our primes
     start = max(start, (_depth+1)|1) # start = max(start, next_odd(_depth))
     end = depth+1 if sqrt > depth > 1 else sqrt+1
     for i in range(start, end, 2):
          #for p in _primes:
          #     if i % p == 0:
          #          break
          #else:
               if num % i == 0:
                    factors[i] += 1
                    return factor(num//i, depth, factors, i) # Restart "sieving" at i
     # Dropped out of loop, num is prime (or no factors below depth)
     if sqrt > depth > 1: # Manual depth, could be missed factor
          if miller_bach(num): # 2*ln(num)^2 Miller-Rabin tests
                    # Under the GRH, this is a deterministic primality test
               factors[num] += 1
               print(("Warning: {} passed the Miller Bach test, which guarantees"
                    +" primality under the GRH").format(num))
          else:
               factors.full = False
               print(("Warning: {} is composite, but the trial factoring depth {}"
                    +" has been reached.").format(num, depth))
               factors[num] += 1
     else: # Guaranteed prime
          factors[num] += 1
     return factors

def is_prime(n, depth=0): # Similar to factor(), except abort after first factor
     '''\
Returns ... if a manual depth is given and there are no factors below that depth.
Tell me if you think of a better idea.'''
     n = _positive(n, "is_prime")

     if n in _primes[:5]: return True
     # Short circuit for very small primes, where sqrt() is long relative to
     # searching the list as below
     if n == 1 or n & 1 == 0: return False

     sqrt = int(sr(n))+1

     for p in _primes:
          if p > sqrt: 
               return True
          if n % p == 0:
               return False

     # Not done yet, do some mangled sort of trial division
     if not prp(n): # 20 of the best prp test implemented here (Miller Rabin ATM)
          return False
     #print("Mangled trial division", n, sqrt, depth)
     start = (_depth+1) | 1 # start = next_odd(_depth)
     end = depth+1 if sqrt > depth > 1 else sqrt+1
     
     sstart = sr(start)
     if _primes[-1] < sstart:
          sieve_max = nt._count # Use whole list
     else:
          sieve_max = _primes.index(next_prime(sstart))
     #print(n, sqrt, start, end, sstart, _primes[-1], _count, sieve_max)
     for i in range(start, end, 2):
          for p in _primes[:sieve_max]: # Sieve div candidates
               if i % p == 0:
                    break
          else:
               #print(i, end, i/end)
               if n % i == 0:
                    return False
     return None if sqrt > depth > 1 else True

def next_prime(num):
     if num <= _primes[-1]:
          for p in _primes:
               if p >= num:
                    return p
     else:
          num |= 1
          while not is_prime(num):
               num += 2
          return num

def gcd(a, b, verbose=False):
     a, b = abs(int(a)), abs(int(b))
     if a < b: a, b = b, a
     if verbose:
          print('GCD('+str(a)+', '+str(b)+') = ...')
          while b > 0:
               print(a, b)
               a, b = b, a % b
     else:
          while b > 0:
               a, b = b, a % b
     return a

def lcm(a, b):
     # ==a*b/gcd(a,b), but minimize intermediate values
     return ( (a // gcd(a, b)) * b)

def min_total_product(n, verbose=False):
# The smallest number a_n such that every i, 1<=i<=n, divides a_n
# aka lcm[1,2,3,...,n-1,n]
     out = 1
     for i in range(2, n+1):
          out *= i//gcd(out, i, verbose)
     return out

def primorial(p=0, n=0):
     out = 1
     if p > 0:
          for i in range(1,p+1):
               if is_prime(i):
                    out *= i
          return out
     elif n > 0:
          i = 2
          while n > 0:
               if is_prime(i):
                    out *= i
                    n -= 1
               i += 1
          return out

def euclid(a, b, verbose=False):
     a, b = abs(a), abs(b)
     if a < b:
          a, b = b, a
          swap = True
     else: swap = False
     if b == 0:
          return a, 1, 0
     else:
          d, w, z = euclid(b, a % b, verbose)
          # d = w*b + z*(a%b)
          # but a%b == a - b*(a//b)
          # so d = wb + za - zb*(a//b)
          # or d = za + b*(w-z(a//b))
          x, y = z, (w - z*(a // b))
          if verbose: print(d, '== {}*{} + {}*{}'.format(x, a, y, b))
          if swap: return d, y, x
          else: return d, x, y

def _euclid(a, b):
     # Attempt it without recursion
     a, b = abs(a), abs(b)
     if a < b:
          a, b = b, a
          swap = True
     else: swap = False
     steps = []
     while b > 0:
            # a, c, b = b, *divmod(a, b)
            tmp = b
            c, b = divmod(a, b)
            a = tmp
            steps.append(c)
     d, x, y = a, 1, 0
     for c in reversed(steps):
          x, y = y, (x - y*c)
     if swap:
          return d, y, x
     else:
          return d, x, y

def solve_congruence(a, b, m, verbose=False):
     # Solve ax==b mod m
     if a > 2**256 or m > 2**256: # _euclid is non-recursive
          d, r, s = _euclid(a, m)
     else:
          d, r, s = euclid(a, m, verbose)
     # d = ar + ms
     #if b == 1 and d == 1:
     #     return pow(a, phi(m)-1, m) # Still more work than the easy way below
     if b % d != 0:
          if verbose: print('There are no solutions to this problem (d={} does not divide b={})'
                         .format(d, b))
          return
     # d|b => b = de
     e = b // d
     # then b = de = (ar+ms)e = a(re) + m(se), => x = re is a solution
     x0 = r*e
     if verbose: print(x0, '== {}*{} is a solution to {}x=={} mod {}'
                    .format(r, e, a, b, m) )
     # by porism 2.7, the full incongruent solutions are 
     # x0+(m/d)n, for n==0,1,2,...,d-1
     c = m // d
     out = []
     for n in range(d):
          out.append((x0 + c*n) % m)
     return sorted(out)

def invert(a, m, verbose=False):
     # Invert a mod m
     x = solve_congruence(a, 1, m, verbose)
     if x:
          return x[0] # unique solution
     return None

def chinese_remainder(blist, mlist, verbose=False):
     M = 1
     # verify pairwise relative primality, and compute M at the same time
     for i in range(len(mlist)):
          M *= mlist[i]
          for j in range(i):
               if gcd(mlist[i], mlist[j]) != 1:
                    print("Error: {} and {} are not coprime"
                         .format(mlist[i], mlist[j]))
                    return
     x = 0; out = []
     for i in range(len(mlist)):
          Mi = M // mlist[i]
          # solve Mi*xi == 1 mod mi (invert Mi)
          xi = invert(Mi, mlist[i])
          x += blist[i]*Mi*xi
          out.append('{}*{}*{}'.format(blist[i],Mi,xi) )
     x %= M
     if verbose: print("x =", ' + '.join(out), "==", x, "mod", M)
     return x

def fermat(n, b=2):
     return pow(b, n, n) == b % n

def euler_prp(n, b=2):
     # According to Euler's criterion (Legendre symbols), if p is an odd prime, then
     # a^((p-1)/2) is congruent to +-1 mod p for any a for which p is not a factor
     res = pow(b, (n-1)//2, n)
     return res == 1 or res == n-1

def miller_rabin(n, b=2):
     # Fermat -> Euler -> Euler-Jacobi/Solovay-Strassen -> Miller-Rabin

     # First find the power of two in n-1
     d = n-1
     s = quick_pow_of_two(d)
     x = pow(b, d, n)
     if x == 1 or x == n-1:
          return True

     for r in range(1, s): # Calculate b^( 2^r * d) for 0 <= r < s
          # x is already b^( 2^0 * d), so just square it to increment r
          x = pow(x, 2, n) # x = modmul(x, x, n)
          if x == 1: # Then x will never be n-1 (and in particular, 2^r*d 
               return False # divides the order of b in n)
          if x == n-1:
               return True
     return False

def miller(n): return miller_bach(n)
def miller_bach(n):
     from math import log
     # This is a deterministic primality test, IF (a subset of) the 
     # Generalized Riemann Hypothesis is true.
     lg = int(2 * log(n)**2)
     for a in range(2, lg+1):
          if not miller_rabin(n, a):
               return False
     return True

def is_composite(n, witnesses=20, base=None):
     # returns the lowest witness of compositeness, else 0 if prp
     if base is not None:
          return 0 if miller_rabin(n, base) else base
     else:
          for p in _primes[:witnesses]: # For the first 'witnesses' primes
               if not miller_rabin(n, p):
                    return p
          return 0

def prp(n, witnesses=20, base=None): 
     # just a wrapper to the above with more intuitive name/value
     return True if not is_composite(n, witnesses, base) else False

def powmod(b, n, m, verbose=False):
     try:
          b = int(b)
          n = int(n)
          m = int(m)
          if n <= 0 or m == 0:
               raise ValueError
     except ValueError:
          raise ValueError('powmod expects positive integer arguments')

     k = n.bit_length() # handy python builtin
     out = 1
     for i in range(k):
          if n & 1:
               out *= b
               out %= m
          #if verbose: print(b, bin(n), out)
          b = b**2 % m
          n >>= 1
     return out

def phi(n):
     # Calculate the Euler totient function using the Euler product
     # phi(n) = n * \prod_{p|n} \frac{p-1}{p}
     out = _positive(n, "phi") # Check that n is a positive int
     if not isinstance(n, Factors): n = factor(n) # Check if n is pre-factored

     # To avoid floating point issues: the denominator p always
     # divides n (by definition), so `out //= denom` is an int, then multiply
     # by the numerator
     for fact in n:
         out //= fact
         out *= (fact - 1)

     return out

def num_divisors(n):
     # Counts the positive divisors of n
     n = _positive(n, "num_divisors") # Check that n is a positive int
     if not isinstance(n, Factors): n = factor(n) # Check if n is pre-factored

     product = 1
     for fact in n:
          product *= (n[fact] + 1)
     return product

def divisors(n):
     # Creates a list of all divisors of n
     # len(this list) == num_divisors(n) (includes 1)
     n = _positive(n, "divisors")
     if not isinstance(n, Factors): n = factor(n)
     
     # Create list by making a list of lists of prime powers for each prime
     # dividing n
     # Then take a "cartesian product" of all these lists, i.e. take all 
     # combinations of one element from each list, i.e. take all combinations
     # of prime powers for each prime dividing n
     biglist = [ [prime**power for power in range(n[prime]+1)] for prime in n]
     # For 72 = 2^3 * 3^2, biglist = [[1, 2, 4, 8], [1, 3, 9]]
  # For 1800 = 2^3 * 3^2 * 5^2, biglist = [[1, 2, 4, 8], [1, 3, 9], [1, 5, 25]]

     divs = [1]
     # Now take all combinations of one element from each sub list
     # Or rather, take all combinations of the first list, then all combinations
     # with the second, etc.
     for lst in biglist:
          divs = [x*y for y in divs for x in lst]
     # That list comprehension syntax is *so* cool
     # For 1800: First iter: divs = [1*1, 1*2, 1*4, 1*8] = [1, 2, 4, 8]
     # Second iter: divs = [1*1, 1*3, 1*9, 2*1, 2*3, 2*9, 4*1, 4*3, 4*9, 8*1,
     # 8*3, 8*9] = [1, 3, 9, 2, 6, 18, 4, 12, 36, 8, 24, 72]
     # Third iter: divs = [1*1, 1*5, 1*25, 3*1, 3*5, 3*25, 9*1, 9*5, 9*25, 2*1,
     # 2*5, 2*25, 6*1, 6*5, 6*25, 18*1, 18*5, 18*25, 4*1, 4*5, 4*25...] and so on
     # All in one, nice, simple, list comprehension
     # Whew!
     return sorted(divs) # Sorting it is the least we can do :)

def sigma(n):
     # Calculates the sum of positive divisors of n
     n = _positive(n, "sigma") # Check that n is a positive int
     if not isinstance(n, Factors): n = factor(n) # Factor n if not done already
     product = 1
     for fact in n:
          product *= ( (fact**(n[fact]+1)-1) // (fact-1) )
     return product

def mu(n):
     # Calculates the Moebius function of n (0 if not square free, +-1 otherwise)
     n = _positive(n, "mu") # Check that n is a positive int
     if not isinstance(n, Factors): n = factor(n) # Factor n if not done already
     if int(n) == 1: return 1
     out = 1
     for fact in n:
          if n[fact] > 1: 
               return 0 # Not square free
          else:
               out = -out
     return out

def perfect(p):
     # Generates the perfect number correspoding to 2^p-1, while checking if
     # Mp is prime.
     if is_prime(p):
          n = (1<<p) - 1
          if is_prime(n):
               return n*(1<<(p-1))
     return False

def rootmod(k, b, m, verbose=True):
     # Solve x^k==b mod m
     # (In the RSA scheme, b is the encrypted message, k is a known exponent,
     # and m is the hard-to-factor public key)
     m = factor(m)
     p = phi(m)
     if verbose: print("phi =", p)
     u = invert(k, p, verbose)
     if not u:
          if verbose: print("(k, phi) != 1")
          return
     else:
          if verbose: print("u =", u)
          out = pow(b, u, int(m))
          
          if gcd(b, m) > 1:
               if verbose: print("b^(ku-1) == {} mod {}".format(pow(b, k*u-1, m), m))
               if out == 0:
                    if verbose: print("(b,m) > 1, and the algorithm produced 0.")
                    return 0
               elif b % int(m) == pow(out, k, int(m)):
                    if verbose: print("Despite (b,m) > 1, the algorithm produced {}, which is correct.".format(out))
                    if mu(m) == 0:
                         if verbose: print("m isn't square free")
                         return out + 2*int(m)
                    else:
                         return out + int(m)
               else:
                    if verbose: print("(b,m) > 1 and the algorithm produced an incorrect answer {}".format(out))
                    return -1
          else: # Guaranteed to be correct
               return out
     # Proof: Assume b^u is a solution. Then b^(ku) == b mod m.
     # Thus b^(ku-1) == 1 mod m --> phi(m) | ku-1 by Euler's Thm (and (b,m)=1).
     # But this is ku == 1 mod phi(m) by definition. So b^u is a solution
     # if u is k-inverse mod phi(m). (This also implies (k, phi(m)) = 1.)
     # Note: As some of the above if statements might suggest, the algorithm still sometimes works even if (b,m) > 1.

def huh(count=100, hi=100, verbose=False):
	# I found that the above algorithm sometimes works when it's not supposed to, 
	# i.e. when (b,m) != 1 and b^(ku-1) =!= 1 mod m. This produces some stats about
	# when that happens.
     from random import randint
     zero, correct, wrong, sqrfree = 0, 0, 0, 0
     tot = count
     while count:
          if verbose: print()
          k, b, m = randint(1,9), randint(1,hi), randint(1,hi)
          x = rootmod(k, b, m, verbose)
          if x is not None: # Ignore (k, phi) > 1
               count -= 1
               if x > m: # (b,m) > 1, but it worked anyways
                    correct += 1
                    if x < 2*m: # m isn't square free
                         sqrfree += 1
               elif x == -1:
                    wrong += 1
               elif x == 0:
                    zero += 1
     print("There were {} zero-results, {} wrong results, {} correct results ({} with a square free modulus), and {} with (b, m) = 1"
          .format(zero, wrong, correct, sqrfree, tot-zero-wrong-correct))

def legendre(a, p):
     if not p & 1 or not is_prime(p): return
     a %= p
     l = pow(a, (p-1)//2, p)
     if l > 1: l -= p
     return l

def descend(A, B, M, p):
     # A^2 + B^2 = Mp     
     # Reduce A, B into [-M/2, M/2]
     u, v = A % M, B % M
     if u > M/2:
          u -= M
     if v > M/2:
          v -= M
     # u^2 + v^2 == A^2 + B^2 == 0 mod M
     # -> u^2 + v^2 = rM for some r
     r = (u*u + v*v) // M
     # Then rM^2p = (u^2 + v^2)(A^2 + B^2) = (uA + vB)^2 + (vA - uB)^2

     # Claims: 1 <= r < M ---- M | uA + vB ---- M | vA - uB
     # Then rp = a^2 + b^2, a = (uA + vB)/M, b = (vA - uB)/M

     return (u*A + v*B) // M, (v*A - u*B) // M, r

     # Proof of claims:
          # 1a) r = (u^2 + v^2)/M <= ((M/2)^2 + (M/2)^2)/M = M/2 < M
          #     (So at most log2(M) descents are required)
          # 1b) r = 0 -> u^2 + v^2 = 0 -> u = v = 0
          #    -> M|A && M|B. But A^2 + B^2 = Mp, so M^2 | Mp -> M = 1
          #    So if r = 0, we were already done.
          # 2) uA + vB == A^2 + B^2 == 0 mod M
          # 3) vA - uB == BA - AB = 0 mod M

def prime_square_sum(p, verbose=False):
     if p == 2: return 1, 1
     elif not is_prime(p): 
          if verbose: print("input {} isn't prime!".format(p))
          return
     # Write p as a sum of two squares
     # Only works if p=1 mod 4
     if p % 4 != 1: 
          if verbose: print("input {} is 3 mod 4!".format(p))
          return
     # p==1[4] -> (-1/p) = 1 -> A^2==-1 [p] has a solution
     # -> p | (A^2 + 1)
     # So solve the quadratic congruence (using a special guessing method for sqrt(-1)).
     # Let A == a^((p-1)/4) [p], 'a' random in [2, p-1]
     # Then A^2 == a^((p-1)/2) == (a/p)
     # -> Half of the time, (a/p) = -1, -> A^2 == -1 and we have a solution
     l, a = 0, 1
     while l != -1:
          a += 1
          l = legendre(a, p) # Evaluated with Euler's Criterion, which is O(log p) with successive squaring
     A, B = pow(a, (p-1)//4, p), 1

     M = (A*A + B*B) // p
     if verbose: print('{}*{} = {}^2 + {}^2'.format(p, M, A, B))
     while M > 1:
          A, B, M = descend(A, B, M, p)
          if verbose: print('{}*{} = {}^2 + {}^2'.format(p, M, A, B))

     if A*A + B*B != p: return "Something went wrong!"
     else:
          A = abs(A)
          B = abs(B)
          if A >= B:
               return A, B
          else:
               return B, A

def square_sum(m, verbose=False):
     # Require all factors == 1 [4]
     # Unless the power is even (d^2m = (da)^2 + (db)^2)
     m = _positive(m, "square_sum")
     if not isinstance(m, Factors): m = factor(m)
     v1 = [] # list of factors that are 1 mod 4
     v3 = [] # the others
     if verbose: print(int(m), '=', m)
     if 2 in m:
          two = m[2]
          del m[2]
     else:
          two = 0
     for p in m:
          if p % 4 == 3:
               if m[p] % 2 == 1:
                    print("input {} has a factor {} which is 3 mod 4 but whose power ({}) isn't even"
                                   .format(int(m), p, m[p]))
                    return
               else:
                    v3.append((p, m[p]))
          else:
               v1.append((p, m[p]))
     
     out = 1, 0
     tmp = 1
     for i in range(two):
          out = square_mul(out, (1,1)) # 2 = 1^2 + 1^2
          tmp *= 2
          if verbose: print("2^{} = {}^2 + {}^2".format(i, *out))
     for p, n in v1:
          ans = prime_square_sum(p, verbose)
          for i in range(n): # If p^n | m and p = a^2 + b^2, then
               out = square_mul(out, ans) # p^n = (a^2 + b^2)^n
               tmp *= p
               if verbose: print("{} = {}^2 + {}^2".format(tmp, *out))

     A, B = out
     for p, n in v3:
          A *= pow(p, n//2)
          B *= pow(p, n//2)
          tmp *= p*p
          if verbose: print("{} = {}^2 + {}^2".format(tmp, A, B))
     
     A, B = abs(A), abs(B)
     if A >= B:
          return A, B
     else:
          return B, A

def square_mul(A, u):
     # (A^2 + B^2)(u^2 + v^2) = (uA + vB)^2 + (vA - uB)^2
     # args are 2-tuples
     #return A[0]*u[0] + A[1]*u[1], abs(u[1]*A[0] - u[0]*A[1])
     # This operation is not unique for arbitrary tuples; swapping the 
     # entry in a tuple gives a different answer.
     # To produce a result that is as balanced as possible, order them.
     if A[0] > A[1]:
          x = A
     else:
          x = A[1], A[0]
     if u[0] > u[1]:
          y = u[1], u[0]
     else:
          y = u
     return x[0]*y[0] + x[1]*y[1], abs(y[1]*x[0] - y[0]*x[1])

def rsa_encrypt(string, *args):
     n, e = args[:2]
     M = bytearray(string.encode())
     l = len(M)
     bits = n.bit_length()
     bytes_per_group = bits//8
     groups = l//bytes_per_group + 1
     pad = bytes_per_group - (l % bytes_per_group)
     print("pad: {}, bpg: {}, len: {}, bits: {}, groups: {}".format(pad, bytes_per_group, l, bits, groups))
     M += bytearray(pad*[b' '])
     arr_of_m = []
     for i in range(groups):
          arr_of_m.append(M[i*bytes_per_group : (i+1)*bytes_per_group])
     arr_of_c = []
     for m in arr_of_m:
          v = int.from_bytes(m, 'little')
          enc = pow(v, e, n) # The actual encryption
          arr_of_c.append(enc.to_bytes(bytes_per_group, 'little'))
     C = b''.join(arr_of_c)
     #print(C)
     #return str(C)[2:-1]
     return C

def rsa_decrypt(string, *args):
     n, e, phi = args[:3]
     #C = bytes(eval('b"'+string+'"'))
     C = string
     bits = n.bit_length()
     l = len(C)
     bytes_per_group = bits//8
     groups = l//bytes_per_group
     arr_of_c = []
     for i in range(groups):
          arr_of_c.append(C[i*bytes_per_group : (i+1)*bytes_per_group])
     arr_of_m = []
     d = invert(e, phi)
     for enc in arr_of_c:
          enc = int.from_bytes(enc, 'little')
          m = pow(enc, d, n) # decrypt (take e-th root mod m)
          arr_of_m.append(m.to_bytes(bytes_per_group, 'little'))
     M = b''.join(arr_of_m)
     return M.decode(errors='ignore').replace('\x00','')

def halve_degree(coeffs, verbose=False):
     '''Takes a list of coefficients, index corresponding to power as usual. 
The list is assumed to be the coeffs from 0 to deg/2 + 1.'''
     coeffs.reverse()
     l = len(coeffs)
     new = [None for i in range(l)]
     for i in range(l-1, -1, -1):
          # http://www.mersennewiki.org/index.php/SNFS_Polynomial_Selection
          # Write b^i + b^-i in terms of (b+1/b)^i, using binomial theorem
          # Then poly = c[i]*(b^i + b^-i) + lower order terms ==
          #      c[i]*((b+1/b)^i - binomial cross terms) + lower order terms
          new[i] = coeffs[i] # So the leading term is the same,
          # and use the binomial cross terms to modify the lower coeffs in place.
          # However: b^(i-1)*b^(-1) = b^(i-2), so (e.g.) for an odd powered
          # term, only odd lower order terms are affected (and same for even)
          k = 0 # Strictly speaking, we could start at k=1 and j=i-2
          for j in range(i, -1, -2):
               coeffs[j] -= new[i] * binomial(i, k)
               k += 1
          if verbose: print(coeffs) # This is why I left the loop conditions as-are,
                        # because watching the terms go to zero is neat.
     return new

from functools import lru_cache

@lru_cache(maxsize=128)
def _binomial(n, k):
     out = 1
     for i in range(k+1, n+1):
          out *= i
     for i in range(2, n-k+1):
          out //= i
     return out

def binomial(n, k):
     if n < 0 or k < 0: 
          return
     # Uniqeify the args before caching them
     if n < k:
          n, k = k, n
     if k < n / 2: # This isn't backwards: look closely at the loops
          k = n - k

     return _binomial(n, k)

def reduce(num, den):
     # Reduce a fraction to lowest terms
     g = gcd(num, den)
     return num//g, den//g

_list = [0, 1]
def fib(n):
     if n < 0:
          raise ValueError("fib needs non-negative integer (not {})".format(n))
     global _list
     l = len(_list)
     if l <= n:
          a, b, c = _list[l-2], _list[l-1], l-1
          while c < n:
               a, b = b, a+b
               c += 1
               _list.append(b)
     return _list[n]
	
#if __name__ == "__main__":
#     from timeit import Timer
#     num1 = int(input('\nEnter a positive integer: '))
#     num2 = int(input('Enter another positive integer: '))
#     d = gcd(num1, num2)
#     print('GCD('+str(num1)+', '+str(num2)+') =', d)
#     print('GCD1 =', str(d)+',', 'GCD2 =', gcd2(num1, num2))
#     print(Timer('gcd(a, b)', 'from gcd import gcd; a = '+str(num1)+'; b = '+str(num2)).timeit())
#     print(Timer('gcd2(a, b)', 'from gcd import gcd2; a = '+str(num1)+'; b = '+str(num2)).timeit())
