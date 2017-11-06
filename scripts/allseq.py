#! /usr/bin/env python3
# -u to force line buffering of stdout

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

import sys


dir = '../website/html/'
ASHTML = dir + 'AllSeq.html'
ASTXT = dir + 'AllSeq.txt'
STATS = dir + 'statistics.html'
JSON = dir + 'AllSeq.json'
STATSON = dir + 'statistics.json'
TMPLT = dir + 'template.html'
STATSTMPLT = dir + 'template2.html'
SEQLIST = dir + 'AllSeqs.txt'
STATEFILE = sys.argv[0] + '.conf'
LOCKFILE = sys.argv[0] + '.lock'
DATEFMT = '%Y-%m-%d %H:%M:%S'


RESPAGE = 'http://www.mersenneforum.org/showpost.php'
RESPOSTIDS = (165249, 397318, 397319, 397320, 397912, 416583, 416585, 416586)


PERHOUR = 55
SLEEPMINUTES = 60
LOOPING = False
TODROP = []
BROKEN = {}
#BROKEN = {747720: (67, 1977171370480)}
# A dict of tuples of {broken seq: (offset, new_start_val)}

################################################################################

from urllib import request, parse, error
from time import strftime, gmtime, sleep, strptime
from collections import Counter
import re, signal, json, os

from _import_hack import add_path_relative_to_script
add_path_relative_to_script('..')
# this should be removed when proper pip installation is supported
from mfaliquot.aliquot import get_guide, get_class, is_driver
from mfaliquot.myutils import linecount, email, Print
from mfaliquot.sequence import Sequence

ERRORMSG = ''

COMPOSITEREGEX = re.compile(r'= <a.+<font color="#002099">[0-9.]+</font></a><sub>&lt;(?P<C>[0-9]+)')
SMALLFACTREGEX = re.compile(r'(?:<font color="#000000">)([0-9^]+)(?:</font></a>)(?!<sub>)')
LARGEFACTREGEX = re.compile(r'(?:<font color="#000000">[0-9^.]+</font></a><sub>&lt;)([0-9]+)')
INFOREGEX = re.compile('<td bgcolor="#BBBBBB">n</td>\n<td bgcolor="#BBBBBB">Digits</td>\n<td bgcolor="#BBBBBB">Number</td>\n</tr><tr><td bgcolor="#DDDDDD">.{1,3}hecked</td>\n<td bgcolor="#DDDDDD">(?P<index>[0-9]+)</td>\n<td bgcolor="#DDDDDD">(?P<size>[0-9]+) <a href="index.php\\?showid=(?P<id>[0-9]+)">\\(show\\)')
CREATEDREGEX = re.compile('([JFMASOND][a-z]{2,8}) ([0-9]{1,2}), ([0-9]{4})') # strftime('%d', strptime(month, "%B"))
#oldpage = re.compile('(<tr> <td>([0-9]+?)</td> <td>([0-9]+?)</td>.*?<td>)[0-9A-Za-z_ ]*?</td> </tr>') # Kept for historical purposes
#oldjson = re.compile(r'(\[([0-9]+?), ([0-9]+?), ([0-9]+?), .*?)[0-9A-Za-z_ ]*?"\]') # Ditto


QUITTING = False
SLEEPING = False
def handler(sig, frame):
     Print(); Print("Recieved signal {}, now quitting".format(sig))
     global QUITTING
     QUITTING = True
     if SLEEPING:
          os.remove(LOCKFILE)
          sys.exit()
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)


def current_update(per_hour):
     this = []
     try:
          with open(STATEFILE, 'r') as conf: # Read which sequences to update
               start = int(conf.readline())
     except FileNotFoundError as e:
          Print('State file not found, starting from sequence 0')
          start = 0
     Print('Start:', start)

     if TODROP: # Remove a sequence from the file
          seqs = []
          with open(SEQLIST, 'r') as f:
               for line in f:
                    num = int(line)
                    if num not in TODROP:
                         seqs.append(num)
          with open(SEQLIST, 'w') as f:
               for seq in seqs:
                    f.write(str(seq)+'\n')

     with open(SEQLIST, 'r') as f:
          for i in range(start): # Skip to line number 'start'
               f.readline()
          for i in range(per_hour):
               try:
                    this.append(int(f.readline()))
               except ValueError: # Error thrown by int() at EOF
                    break
     return this, start


def get_reservations(pids):
     reserves = {}
     for pid in pids:
          page = blogotubes(RESPAGE + '?p={}&postcount=1'.format(str(pid)),
                    hdrs={'User-Agent': 'Dubslow/AliquotSequences'})
          update = re.search(r'<!-- edit note -->.*Last fiddled with by [A-Za-z_0-9 -]+? on ([0-9a-zA-Z -]+) at <span class="time">([0-9:]{5})</span>', page, flags=re.DOTALL)
          updated = update.group(1)+' '+update.group(2)
          # Isolate the [code] block with the reservations
          page = re.search(r'<pre.*?>(.*?)</pre>', page, flags=re.DOTALL).group(1)
          for line in page.splitlines():
               herp = re.match(r' {0,3}([0-9]{3,7})  ([0-9A-Za-z_@. -]{1,16})', line) # "seq name"
               try:
                    name = herp.group(2)
               except: pass # Ignore non-matching lines
               else:
                    if 'jacobs and' in name:
                         name = 'jacobs and Richard Guy'
                    reserves[int(herp.group(1))] = name.strip()
     return reserves, updated


def get_old_info(JSON, reserves, this, drop):
     data = []; tmp = {}; oldinfo = []
     with open(JSON, 'r') as f: # Read current table data
          olddat = json.load(f)['aaData']
     if olddat:
          for dat in olddat:
               ali = Sequence(lst=dat)
               seq = ali.seq
               if seq not in this and seq not in drop: # If this sequence is not about to be
                   ali.res = reserves.get(seq, '')     # updated, save its current data
                   data.append(ali)
               elif seq in this:
                    tmp[seq] = ali
          for seq in this: # This and the above line serve to re-add any sequences lost due to garbage (edit: and also newly-extended sequences with no data)
               try:
                    oldinfo.append(tmp[seq])
               except KeyError:
                    oldinfo.append(Sequence(seq=seq, index=-1))
          return data, oldinfo


def guide(string):
     """Returns a tuple of (str_of_guide, class_with_powers, is_driver)"""
     if 'terminated' in string:
          return "Terminated?", -9, True
     elif 'Garbage' in string:
          return "Garbage", -9, False
     else:
          dr = get_guide(string, powers=False) # dr is an instance of "Factors"
          drs = str(dr) # str specified by "Factors" class
          if drs == '2':
               return "Downdriver!", 1, False
          else:
               return drs, get_class(string), is_driver(guide=dr)


def cofactor(s):
     out = [ int(t[1:]) for t in [t.strip() for t in s.split('*')] if t[0] == 'C' ] # forall stripped sections of s separated by '*': if the first character is 'C', return the int in the rest of the section
     return out[0] if len(out) == 1 else None # Be sure there is exactly one cofactor


def blogotubes(url, encoding='utf-8', hdrs=None):
     global ERRORMSG, QUITTING
     if hdrs is None:
          hdrs = {'User-Agent': 'MersenneForum/Dubslow/AliquotSequences'}
     req = request.Request(url, headers = hdrs )
     try:
          page = request.urlopen(req).read().decode(encoding)
     except error.HTTPError as e:
          ERRORMSG += 'HTTPError: '+str(e)+'\n'
          Print('HTTPError:', e)
          QUITTING = True
          return None
     except Exception as e:
          ERRORMSG += 'Error! '+str(e)+'\n'
          Print('Error!', e)
          QUITTING = True
          return None
     else:
          return page


def id_created(i):
     i = str(i)
     #Print('Querying id', i)
     page = blogotubes('http://factordb.com/frame_moreinfo.php?id='+i)
     date = CREATEDREGEX.search(page)
     year = date.group(3)
     day = date.group(2)
     if len(day) == 1: day = '0'+day
     month = strftime('%m', strptime(date.group(1), '%B'))
     return '-'.join(iter((year, month, day)))


def check(old, tries=3, reserves=None, special=None):
     if tries <= 0:
          Print('Bad sequence or id! Seq:', old.seq)
          return old
     if old.id is None or old.id == 0 or special:
          return updateseq(old, reserves)
     # else:
     page = blogotubes('http://factordb.com/index.php?id='+str(old.id))
     if QUITTING: return old
     if 'CF' in page: # Line unfactored, no progress since last update
          old.time = strftime(DATEFMT, gmtime())
          if isinstance(old.progress, int):
               old.progress = id_created(old.id)
          return old
     elif 'FF' in page or 'P' in page:
          return updateseq(old, reserves)
     else:
          return check(old, tries-1, special)


def updateseq(old, reserves):
     global ERRORMSG, QUITTING
     tries = 5
     if old.seq in BROKEN:
          seq = BROKEN[old.seq][1]
          borked = True
     else:
          seq = old.seq
          borked = False
     while tries:
          page = blogotubes('http://factordb.com/sequences.php?se=1&action=last&aq='+str(seq))
          if QUITTING: return old
          if 'Resources used by your IP' not in page:
               info = INFOREGEX.search(page)
               comps = COMPOSITEREGEX.findall(page)
               smalls = SMALLFACTREGEX.findall(page)
               bigs = LARGEFACTREGEX         .findall(page)
               if info: # Make sure we can actually get size/index info before in depth parsing
                    ali = Sequence(seq=seq, size=int(info.group('size')), index=int(info.group('index')), id=int(info.group('id')))
                    ali.time = strftime(DATEFMT, gmtime())
                    ali.res = reserves.get(seq, '')
                    if 'Not all factors known' in page:
                         factors = ''; size = 2

                         try:
                              factors += smalls[0]
                              for small in smalls[1:]:
                                   factors += " * "+small
                                   size += len(small)
                         except: # Happens if no regex match
                              Print('Seq:', seq, "no smalls match")
                              tries -= 1
                              if tries == 0:
                                   Print('>'*10 + 'ERROR NO SMALL FACTORS')
                                   ERRORMSG += 'Seq {} had no smalls too many times\n'.format(seq)
                                   return old
                              else:
                                   Print('Retrying ('+str(tries), 'tries left)')
                              sleep(5)
                              continue

                         if bigs:
                              for big in bigs:
                                   factors += " * P"+big
                                   size += int(big)

                         if comps:
                              for comp in comps:
                                   factors += ' * C'+comp
                                   cofact = int(comp)
                                   size += cofact
                         else:
                              cofact = 0
                              Print('Seq:', seq, "no comps match")
                              Print('Seq:', seq, "no smalls match")
                              tries -= 1
                              if tries == 0:
                                   Print('>'*10 + 'ERROR NO COMPOSITES FOUND')
                                   ERRORMSG += 'Seq {} had no composite too many times\n'.format(seq)
                                   return old
                              else:
                                   Print('Retrying ('+str(tries), 'tries left)')
                              sleep(5)
                              continue
                         # ~~Note to self: handle lack of regex matches in same fashion as below~~
                         # ^ Only took several years to accomplish this

                         # Now some sanity checks
                         if size < 0.9*ali.size: # Garbage values
                              Print('Seq:', seq, 'index:', ali.index, 'size:', ali.size, 'garbage factors found:', factors, 'cofact:', cofact)
                              factors = "Garbage values"
                              tries -= 1
                              if tries == 0:
                                   Print('>'*10 + 'ERROR BAD SEQ MATCH')
                                   ERRORMSG += 'Seq {} had garbage values too many times\n'.format(seq)
                                   return old
                              else:
                                   Print('Retrying ('+str(tries), 'tries left)')
                              sleep(5)
                              continue
                         elif cofact == 0: # No cofactors
                              Print('Seq:', seq, 'cofactors? facts:', factors, 'cofact:', cofact)
                              tries -= 1
                              if tries == 0:
                                   Print('>'*10 + 'ERROR NO COFACTOR')
                                   ERRORMSG += 'Seq {} had no cofactor\n'.format(seq)
                                   return old
                              else:
                                   Print('Seq:', seq, 'no cofactor, retrying ({} tries left) factors: {}'.format(tries, factors))
                              sleep(5)
                              continue
                         elif cofact < 65: # Small cofactor, FDB will auto-factor it
                              tries -= 1
                              if tries == 0:
                                   Print('>'*10 + 'ERROR SMALL COFACTOR')
                                   ERRORMSG += 'Seq {} had a small cofactor\n'.format(seq)
                                   return old
                              else:
                                   Print('Seq:', seq, 'small cofactor, retrying ('+str(tries), 'tries left) factors:', factors)
                              sleep(5)
                              continue
                         elif 0 < tries < 3:
                              Print('Seq:', seq, 'retry factors:', factors)

                         # Perfectly sane sequence
                         ali.factors = factors
                         ali.cofact = cofact
                         ali.progress = ali.index - old.index
                         ali.guide, ali.clas, ali.driver = guide(factors)
                         if borked:
                              ali.seq = old.seq
                              ali.res = reserves.get(old.seq, '')
                              ali.index += BROKEN[old.seq][0]
                              ali.progress += BROKEN[old.seq][0]
                         if ali.progress <= 0: ali.progress = id_created(ali.id)
                    else: # No 'Resources', no 'Not all factors known'
                         Print('Seq:', seq, 'Strange. Termination? More likely a bad sequence.')
                         ali.factors = "Reportedly terminated"
                         ali.guide, ali.clas, ali.driver = 'Terminated?', -5, True
                         ali.progress = 'Terminated?'
                         ERRORMSG += 'Supposedly, seq {} has terminated!!!'.format(seq)
                    return ali
          else: # Reached query limit
               Print('Seq:', seq, 'the DB is refusing requests.')
               ERRORMSG += 'Reached query or cpu limit. Oops.\n'
               try:
                    # pages = re.search(r'>Page requests</td>\n<td[^>]*?>([0-9,]+)</td>', page).group(1)
                    # ^ avoid repeating the entire regex 5 times with slight variations. very typo prone.
                    retmpl = r'>{}</td>\n<td[^>]*?>{}</td>'
                    pages, ids, queries, cputime, when = [re.search(retmpl.format(name, valgroup), page).group(1) for name, valgroup in (
                                                          (r'Page requests',           r'([0-9,]+)'),
                                                          (r'IDs created',             r'([0-9,]+)'),
                                                          (r'Database queries',        r'([0-9,]+)'),
                                                          (r'CPU \(Wall clock time\)', r'([0-9,.]+) seconds'),
                                                          (r'Counting since',          r'(.*?)'))]
                    Print("{} page reqs, {} new ids, {} db queries, {} cputime since {}".format(pages, ids, queries, cputime, when))
               except AttributeError: # some re.search() failed
                    Print('Not only is it refusing requests, but its formatting has changed!')
               QUITTING = True
               return old


def inner_main(special=None):
     global ERRORMSG
     print('\n'+strftime(DATEFMT))
     total = linecount(SEQLIST)
     if special:
          this = special
     else:
          this, start = current_update(PERHOUR)
     reserves, updated = get_reservations(RESPOSTIDS)
     data, oldinfo = get_old_info(JSON, reserves, this, TODROP)
     Print('Init complete, starting FDB queries')

     count = 0
     for old in oldinfo: # Loop over every sequence to be updated
          # never-before-checked sequences have index -1 (see get_old_info()) and if such a seq errors, there's no data here: ignore it.
          if QUITTING:
               if old.index > 0:
                    data.append(old)
               continue

          ali = check(old, reserves=reserves, special=special)
          if ali and ali.index > 0:
               data.append(ali)
               if not QUITTING:
                    count += 1
                    Print(count, 'sequences complete:', old.seq)
          sleep(1)

     with open(TMPLT, 'r') as f: # Read in webpage templates
          html = f.read()
     with open(STATSTMPLT, 'r') as f:
          stats = f.read()

     #dato = {ali.seq: ali for ali in data}
     #data = [dato[seq] for seq in set(dato.keys())]
     # Now get all the stats (i.e. count all the instances of stuff)
     sizes = Counter(); lens = Counter(); guides = Counter(); progs = Counter(); cofacts = Counter()
     totsiz = 0; totlen = 0; avginc = 0; totprog = 0; txtdata = ''
     for ali in sorted(data, key=lambda ali: ali.seq):
          sizes[ali.size] += 1; totsiz += ali.size
          lens[ali.index] += 1; totlen += ali.index
          guides[ali.guide] += 1; avginc += ali.index/ali.size
          progs[ali.progress] += 1
          cofacts[ali.cofact] += 1
          txtdata += str(ali)

          if isinstance(ali.progress, int):
               totprog += 1

     # Create broken sequences HTML
     if BROKEN:
          # horizontal table: create a list of tuples containing each column (i.e. each sequence)
          entries = (('''<a href="http://factordb.com/sequences.php?se=1&aq={}&action=last20">{}</a>'''.format(BROKEN[seq][1], seq), str(BROKEN[seq][0])) for seq in sorted(BROKEN))
          row1, row2 = zip(*entries) # zip converts column data into row order
          r1 = ''.join('<td>{}</td>'.format(datum) for datum in row1)
          r2 = ''.join('<td>{}</td>'.format(datum) for datum in row2)
          borken_html = '<table><tr><th scope="row">Sequence</th>{}</tr><tr><th scope="row">Index offset</th>{}</tr></table>'.format(r1, r2)
          unborken_html = ''
     else:
          borken_html = ''
          unborken_html = 'none currently.'

     html = html.format(updated, unborken_html, borken_html) # Imbue the template with the reservation time and broken sequences

     # Put stats table in json-able format
     lentable = []; lencount = 0
     sizetable = [ [key, value] for key, value in sizes.items() ]
     cofactable = [ [key, value] for key, value in cofacts.items() ]
     for leng, cnt in sorted(lens.items(), key=lambda tup: tup[0]):
          lentable.append( [leng, cnt, "{:2.2f}".format(lencount/(total-cnt)*100)] )
          lencount += cnt
     guidetable = [ [key, value] for key, value in guides.items() ]
     progtable = [ [key, value] for key, value in progs.items() ]
     stats = stats.format(totinc=totlen/totsiz, avginc=avginc/total, totprog=totprog, progcent=totprog/total)

     # Write all the data and webpages
     with open(ASHTML, 'w') as f:
          f.write(html)
     with open(ASTXT, 'w') as f:
          f.write(txtdata)
     with open(STATS, 'w') as f:
          f.write(stats)
     with open(JSON, 'w') as f:
          f.write(json.dumps({"aaData": data}).replace('],', '],\n')+'\n')
     with open(STATSON, 'w') as f:
          f.write(json.dumps({"aSizes": sizetable, "aCofacts": cofactable, "aGuides": guidetable, "aProgress": progtable, "aLens": lentable}).replace('],', '],\n')+'\n')

     # Cleanup
     if not special:
          start += count
          if start >= total:
               start = 0
          if count != PERHOUR and start != 0:
               ERRORMSG += 'Something went wrong. Only {} seqs were updated.\n'.format(count)
          Print("Next start is", start)
          with open(STATEFILE, 'w') as conf: # Save how many sequences we updated
               conf.write(str(start)+'\n')

     if ERRORMSG:
          try:
               email('Aliquot failure!', ERRORMSG)
          except Exception as e:
               Print('Email failed:', e)
               Print('Message:\n', ERRORMSG)

     Print('Written HTML and saved state.')


################################################################################
# Start actual code execution

def main():
     global LOOPING, SLEEPING
     if os.path.exists(LOCKFILE):
          Print("Didn't start: lockfile is present")
          sys.exit(-1)

     open(LOCKFILE, 'a').close()

     try:
          special = [int(arg) for arg in sys.argv[1:]]
     except ValueError:
          print('Error: Args are sequences to be run')
          os.remove(LOCKFILE)
          sys.exit(-1)

     if special:
          LOOPING = False
     else:
          special = None

     while True:
     # This means you can start it once and leave it, but by setting LOOPING = False you can make it one-and-done
     # This would be a good place for a do...while syntax
          try:
               inner_main(special)
          except Exception:
               raise # Errors are unhandled except to interrupt a sleeping loop, and to cleanup via finally
          finally:
               os.remove(LOCKFILE)

          if LOOPING and not QUITTING:
               Print('Sleeping.')
               SLEEPING = True
               sleep(SLEEPMINUTES*60)
               SLEEPING = False
          else:
               break

if __name__ == '__main__':
     main()
