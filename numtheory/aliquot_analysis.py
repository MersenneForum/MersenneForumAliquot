#! /usr/bin/env python3

def tau(p):
     '''Indirectly calculates tau(p) by examining p mod powers of 2 (only works on odd primes)'''
     # p === -1 mod 2^x => tau >= x
     # p =!= -1 mod 2^x => tau < x
     # so 
     x = 2
     pow2 = 4
     while p % pow2 == pow2 - 1:
          x += 1
          pow2 <<= 1
     return x - 1

# The former is essentially the best way to find the latter bi-condition

def conditions_on_prime_if_tau_is_lte_x(x):
     ''' returns (residue, modulus) meaning any prime with tau <= x, then p
         must be `residue` mod `modulus`'''
     if x < 1: raise ValueError('x must be at least 1 (got {})'.format(x))
     # tau(p) = x <=> p+1 === 2^x mod 2^x+1
     m = 1 << x
     return m - 1, m << 1


def probable_semiprime_tau(n, x):
     '''Tests if the semi prime of unknown composition n=pq could possibly
        have tau(n) = x. False guarantees tau != x, but True does not 
        guarantee tau = x.'''
     # tau(n) = tau(p) + tau(q) (=> tau(n) >= 2 right off the bat
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
          r1s = [(r1+i*m1) % m2 for i in range(m2//m1)]
          #print('x = {}, x1 = {}, x2 = {}, m2 = {}, r2 = {}, r1s = {}'.format(x, x1, x2, m2, r2, r1s))
          for r1 in r1s:
               r = (r2*r1) % m2
               if n % m2 == r:
                    print("Given that n%{}={}, it's possible that p%{}={} and q%{}={}, meaning tau(p)={} and tau(q)={}, meaning tau(n) may yet be {}"
                         .format(m2, r, m2, r1, m2, r2, x1, x2, x))
                    allowable_residues.append((m2, (r1, r2)))
     return allowable_residues

def probable_semiprime_tau_lte_x(n, xprime):
     return [(x, allowed_residues) for x in range(2, xprime+1) for allowed_residues in probable_semiprime_tau(n, x)]
