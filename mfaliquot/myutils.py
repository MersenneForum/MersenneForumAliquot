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

def ggnfs_estimate(totyield, qdone, qrange, secperrel, total=False):
     #print("secperrel", secperrel, "qdone:", qdone, "totyield:", totyield)
     currtime = secperrel * totyield
     if total:
          eta = int(currtime/qdone * qrange)
     else:
          eta = int(currtime/qdone * (qrange-qdone))
     days, eta = divmod(eta, 3600*24)
     hours, eta = divmod(eta, 3600)
     mins, eta = divmod(eta, 60)
     secs = eta
     out = "ETA: "
     if days > 0:
          print("ETA: {:d} days and {:d}h {:02d}m {:02d}s".format(days, hours, mins, secs))
     elif hours > 0:
          print("ETA: {:d}:{:02d}:{:02d}".format(hours, mins, secs))
     else:
          print("ETA: {:d}:{:02d}".format(mins, secs))

if __name__ == '__main__':
     from sys import argv
     qrange = int(argv[1])
     for file in argv[2:]:
          qstart = int(file.split('.')[0])*1000
          with open(file, 'r') as f:
               last = f.read().split('\n')[-1]
          last = last.split()
          totyield = int(last[2][:-1])
          qcurr = int(last[3][2:])
          rate = float(last[4][1:])
          ggnfs_estimate(totyield, qcurr-qstart, qrange, rate)

def linecount(file):
     lines = 0
     with open(file, 'r') as f:
          while f.readline():
               lines += 1
     return lines

def asciistr(s):
     try:
          n = [chr(int(b)) for b in s.split()]
     except ValueError:
          n = [chr(int(b,16)) for b in s.split()]
     return ''.join(n)

def tobytes(s):
     try:
          n = int(s,16)
     except ValueError:
          n = int(s)
     c = []
     while n:
          c.append(n & 0xFF)
          n >>= 8
     return c

def subreddit(s):
     l = [tobytes(x) for x in s.split()]
     for n in l:
          n.reverse()
     m = [x for ls in l for x in ls] # flatten l
     return ''.join([chr(x) for x in m])

def anagram(s):
     from itertools import permutations as p
     return [''.join(x) for x in p(s)]

def snfs(s, g):
     s *= 0.59
     s = int(s)
     s += 30
     print(s, g)
     return s <= g

def _len(n): # digits in n
     return len(str(abs(int(n))))

def opnpoly(k, b, n, c, deg, hi=None):
     # Create an SNFS poly for k*b^n+c with given degree. This is based largely
     # on http://www.mersenneforum.org/showpost.php?p=54606&postcount=39 and
     # http://www.mersenneforum.org/showthread.php?t=15773.
     # Currently it only works for prime b & n, n > 13. (Rather, results are
     # guaranteed to be pseudo-optimal only under those conditions. The code 
     # will work in some other cases, but it might not be the best option. I
     # plan to add in some other cases later.)

     N = k * b**n + c
     out = "c{deg}: {cdeg}\nc0: {c0}\nm: {m}\nskew: {skew}\ntype: snfs\nsize: {size}"

     def low_poly(k, b, n, c, N, deg):      
          # Round down to multiple of deg
          m, cdeg = divmod(n, deg)
          m = b**m
          cdeg = k * b**cdeg
          skew = (abs(c/cdeg))**(1/deg)
          return {'deg': deg, 'cdeg': cdeg, 'c0': c, 'm': m, 'skew': skew, 'size': _len(N)}, max(abs(cdeg), abs(c))

     def hi_poly(k, b, n, c, N, deg):
          # Round up to multiple of deg, increase difficulty
          xtra = ((deg - (n % deg)) % deg)
          N *= b**xtra
          cdeg = k
          c0 = b**xtra * c
          m = b**((n+xtra)//deg)
          skew = (abs(c0/cdeg))**(1/deg)
          return {'deg': deg, 'cdeg': cdeg, 'c0': c0, 'm': m, 'skew': skew, 'size': _len(N)}, max(abs(cdeg), abs(c0)), xtra

     if hi is not None and not hi: # User only wants smaller size poly
          print(out.format(**low_poly(k,b,n,c,N,deg)[0]))

     elif hi: # User only wants larger size poly
          print(out.format(**hi_poly(k,b,n,c,N,deg)[0]))

     else: # User wants to let this function decide

          score = [None, None] # Largest algebraic coefficient for each poly
          polys = [None, None]
          polys[0], score[0] = low_poly(k,b,n,c,N,deg)
          polys[1], score[1], xtra = hi_poly(k,b,n,c,N,deg)

          if score[0] <= score[1]:
               print("I recommend the following polynomial:")
               print(out.format(**polys[0]))
          else:
               if _len(b) * xtra > 5: # Rather spurious decision
                    print("Warning: this poly has a significantly larger difficulty than the number",
                          "in question, consider doing some test sieving")
               else:
                    print("I recommend the following polynomial:")
               print(out.format(**polys[1]))

from time import strftime
def Print(*args):
     print(strftime('%H:%M:%S'), *args)

from urllib import request, parse, error
from http.cookiejar import CookieJar
def add_cookies():
     request.install_opener(request.build_opener(request.HTTPCookieProcessor(CookieJar())))

def blogotubes(url, encoding='utf-8', hdrs=None, data=None):
     if hdrs is None:
          #hdrs = {'User-Agent': 'Dubslow'}
          hdrs = {}
     if data is not None:
          data = parse.urlencode(data, encoding=encoding)
          data = data.encode(encoding)
          #hdrs['Content-Type'] = 'application/x-www-form-urlencoded;charset='+encoding
     #req = request.Request(parse.quote(url, safe='/:'), headers=hdrs)
     req = request.Request(url, headers=hdrs)
     try:
          page = request.urlopen(req, data).read().decode(encoding)
     except error.HTTPError as e:
          Print('HTTPError:', e)
          return None
     except Exception as e:
          Print('{}!'.format(type(e)), e)
          return None
     else:
          return page

host ='smtp.gmail.com'
port = 587
mode = 'tls'
acc = '<sthg>@gmail.com'
pw = ''

def email(*args): # HTML, attachments, cc?
     '''(Subject, Message) or (Recipient, Subject, Message)'''
     if len(args) == 2:
          send_email(acc, acc, args[0], args[1], host, port, True, acc, pw)
     elif len(args) == 3:
          send_email(args[0], acc, args[1], args[2], host, port, True, acc, pw)
     else:
          raise ValueError("email() expects two or three arguments")

import smtplib
from email.utils import formatdate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(to, frm, sbjct, txt, host, port, tls=True, acct=None, pswd=None):
     """To, From, Subject, Body, Server, Port, Account, Password"""
     msg = MIMEMultipart()

     if isinstance(to, list):
          to = ', '.join(to)
     msg['To'] = to
     msg['Subject'] = sbjct
     msg['From'] = frm
     msg['Date'] = formatdate(localtime=True)

     msg.attach(MIMEText(txt))

     server = smtplib.SMTP(host, port)
     if tls:
          server.starttls()
     if acct or pswd:
          server.login(acct, pswd)
     server.send_message(msg)
