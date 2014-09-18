#! /usr/bin/python3 -u
# -u to force line buffering of stdout

from urllib import request, parse, error
from time import strftime, gmtime, sleep, strptime
from collections import Counter
from aliquot import get_guide, get_class, is_driver
from myutils import linecount, email, Print
import re, sys, signal, json
dir = './'
FILE = dir + 'AllSeq.html'
TXT = dir + 'AllSeq.txt'
STATS = dir + 'statistics.html'
JSON = dir + 'AllSeq.json'
STATSON = dir + 'statistics.json'
template = dir + 'template.html'
template2 = dir + 'template2.html'
seqfile = dir + 'AllSeqs.txt'
datefmt = '%Y-%m-%d %H:%M:%S'

per_hour = 55
sleep_time = 60
total = linecount(JSON)
special = [] # If I need to update a specific set of sequences
loop = False
drop = []
broken = {319860: (2825523558447041736665230216235917892232717165769067317116537832686621082273062400083298623866666431871912457614030538, 1073)}
#broken = {747720: (1977171370480, 67)}
# A dict of tuples of {broken seq: (new_start_val, offset)}
error_msg = ''

for arg in sys.argv[1:]:
     try:
          special.append(int(arg))
     except ValueError:
          print('Error: Args are sequences to be run')
          sys.exit(-1)

composite = re.compile(r'= <a.+<font color="#002099">[0-9.]+</font></a><sub>&lt;(?P<C>[0-9]+)')
smallfact = re.compile(r'(?:<font color="#000000">)([0-9^]+)(?:</font></a>)(?!<sub>)')
largefact = re.compile(r'(?:<font color="#000000">[0-9^.]+</font></a><sub>&lt;)([0-9]+)')
stuff = re.compile('<td bgcolor="#BBBBBB">n</td>\n<td bgcolor="#BBBBBB">Digits</td>\n<td bgcolor="#BBBBBB">Number</td>\n</tr><tr><td bgcolor="#DDDDDD">.{1,3}hecked</td>\n<td bgcolor="#DDDDDD">(?P<index>[0-9]+)</td>\n<td bgcolor="#DDDDDD">(?P<size>[0-9]+) <a href="index.php\\?showid=(?P<id>[0-9]+)">\\(show\\)')
created = re.compile('([JFMASOND][a-z]{2,8}) ([0-9]{1,2}), ([0-9]{4})') # strftime('%d', strptime(month, "%B"))
#oldpage = re.compile('(<tr> <td>([0-9]+?)</td> <td>([0-9]+?)</td>.*?<td>)[0-9A-Za-z_ ]*?</td> </tr>') # Kept for historical purposes
#oldjson = re.compile(r'(\[([0-9]+?), ([0-9]+?), ([0-9]+?), .*?)[0-9A-Za-z_ ]*?"\]') # Ditto

class Sequence(list):
     _map = {'seq': 0,
             'size': 1,
             'index': 2,
             'id': 3,
             'guide': 4,
             'factors': 5,
             'cofact': 6,
             'clas': 7,
             'time': 8,
             'progress': 9,
             'res': 10,
             'driver': 11 }
     
     def __setattr__(self, name, value): # Black magic meta programming to make certain attributes access the list
          try:                           # (This is why I love Python.)
               self[Sequence._map[name]] = value
          except KeyError:
               object.__setattr__(self, name, value)
     
     def __getattribute__(self, name):
          try:
               return self[Sequence._map[name]]
          except KeyError:
               return object.__getattribute__(self, name)
     
     def __init__(self, seq=0, size=0, index=0, id=0, guide=None, factors=None, time=None, lst=None):
          if lst is not None:
               super().__init__(lst)
               if seq: self.seq = seq
               if index: self.index = index
               if size: self.size = size
               if time: self.time = time
               if factors: self.factors = factors
               if id: self.id = id
               if guide: self.guide = guide
          else:
               super().__init__([None for i in range(len(Sequence._map))])
               self.seq = seq
               self.index = index
               self.size = size
               self.id = id
               self.guide = guide
               self.time = time
               self.factors = factors
               self.res = ''
               self.driver = ''
               self.progress = 'Unknown'
     
     def well_formed(self):
          return self.seq and self.size and self.index and self.factors
     
     def __str__(self):
          if self.well_formed():
               return "{:>6d} {:>5d}. sz {:>3d} {:s}\n".format(ali.seq, ali.index, ali.size, ali.factors)
          else:
               raise AttributeError('Not fully described! Seq:', self.seq)
     
quitting = False
sleeping = False
def handler(sig, frame):
     global quitting
     quitting = True
     if sleeping:
          sys.exit()
signal.signal(signal.SIGTERM, handler); signal.signal(signal.SIGINT, handler)

def current_update(per_hour):
     this = []
     with open(sys.argv[0]+'.conf', 'r') as conf: # Read which sequences to update
          start = int(conf.readline())
          Print('Start:', start)

     if drop: # Remove a sequence from the file
          seqs = []
          with open(seqfile, 'r') as f:
               for line in f:
                    num = int(line)
                    if num not in drop:
                         seqs.append(num)
          with open(seqfile, 'w') as f:
               for seq in seqs:
                    f.write(str(seq)+'\n')

     with open(seqfile, 'r') as f:
          for i in range(start): # Skip to line number 'start'
               f.readline()
          for i in range(per_hour):
               try:
                    this.append(int(f.readline()))
               except ValueError: # Error thrown by int() at EOF
                    break
     return this, start

def get_reservations():
     reserves = {}
     page = blogotubes('http://www.mersenneforum.org/showpost.php?p=165249&postcount=1', 
               hdrs={'User-Agent': 'Dubslow/AliquotSequences'})
     update = re.search(r'<!-- edit note -->.*Last fiddled with by [A-Za-z_0-9 -]+? on ([0-9a-zA-Z ]+) at <span class="time">([0-9:]{5})</span>', page, flags=re.DOTALL)
     updated = update.group(1)+' '+update.group(2)
     page = re.search(r'<pre.*?>(.*?)</pre>', page, flags=re.DOTALL).group(1)
     # Isolate the [code] block with the reservations
     for line in page.splitlines():
          herp = re.match(r' {0,3}([0-9]{3,6})  ([0-9A-Za-z_. -]{1,16})', line) # "seq name"
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
          for seq in this: # This and the above line serve to re-add any sequences lost due to garbage
               try:
                    oldinfo.append(tmp[seq])
               except KeyError:
                    oldinfo.append(Sequence(seq, index=-1))
          return data, oldinfo
          
def guide(string):
     """Returns a tuple of (str_of_guide, class_with_powers, is_driver)"""
     if 'terminated' in string:
          return "Terminated?", -9, True
     elif 'Garbage' in string:
          return "Garbage", -9, False
     else:
          dr = get_guide(string, powers=False) # dr is an instance of "Factors"
          if get_class(guide=dr) > 3: 
               drs = '2^{}'.format(dr[2]) # Replace an unstable "guide" with simply 2^n
          else:
               drs = str(dr) # str specified by "Factors" class
          if drs == '2':
               return "Downdriver!", 1, False
          else:
               return drs, get_class(string), is_driver(guide=dr)

def cofactor(s):
     out = [ int(t[1:]) for t in [t.strip() for t in s.split('*')] if t[0] == 'C' ] # forall stripped sections of s separated by '*': if the first character is 'C', return the int in the rest of the section
     return out[0] if len(out) == 1 else None # Be sure there is exactly one cofactor

def blogotubes(url, encoding='utf-8', hdrs=None):
     global error_msg
     if hdrs is None:
          hdrs = {'User-Agent': 'MersenneForum/Dubslow/AliquotSequences'}
     global quitting
     req = request.Request(url, headers = hdrs )
     try:
          page = request.urlopen(req).read().decode(encoding)
     except error.HTTPError as e:
          error_msg += 'HTTPError: '+str(e)+'\n'
          Print('HTTPError:', e)
          quitting = True
          return None
     except Exception as e:
          error_msg += 'Error! '+str(e)+'\n'
          Print('Error!', e)
          quitting = True
          return None
     else:
          return page

def id_created(i):
     i = str(i)
     #Print('Querying id', i)
     page = blogotubes('http://factordb.com/frame_moreinfo.php?id='+i)
     date = created.search(page)
     year = date.group(3)
     day = date.group(2)
     if len(day) == 1: day = '0'+day
     month = strftime('%m', strptime(date.group(1), '%B'))
     return '-'.join(iter((year, month, day)))

def check(old, tries=3):
     if tries <= 0: 
          Print('Bad sequence or id! Seq:', old.seq)
          return old
     if old.id is None or old.id == 0 or special:
          return updateseq(old)
     # else:
     page = blogotubes('http://factordb.com/index.php?id='+str(old.id))
     if quitting: return old
     if 'CF' in page: # Line unfactored, no progress since last update
          old.time = strftime(datefmt, gmtime())
          if isinstance(old.progress, int):
               old.progress = id_created(old.id)
          return old
     elif 'FF' in page or 'P' in page:
          return updateseq(old)
     else:
          return check(old, tries-1)

def updateseq(old):
     global error_msg
     tries = 5
     if old.seq in broken:
          seq = broken[old.seq][0]
          borked = True
     else:
          seq = old.seq
          borked = False
     while tries:
          page = blogotubes('http://factordb.com/sequences.php?se=1&action=last&aq='+str(seq))
          if quitting: return old
          if 'Resources used by your IP' not in page:
               info = stuff.search(page)
               comps = composite.findall(page)
               smalls = smallfact.findall(page)
               bigs = largefact.findall(page)
               if info: # Make sure we can actually get size/index info before in depth parsing
                    ali = Sequence(seq, int(info.group('size')), int(info.group('index')), int(info.group('id')))
                    ali.time = strftime(datefmt, gmtime())
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
                         # Note to self: handle lack of regex matches in same fashion as below
                         # Also why do I even need cofactor()? derp derp

                         # Now some sanity checks
                         if size < 0.9*ali.size: # Garbage values
                              Print('Seq:', seq, 'index:', ali.index, 'size:', ali.size, 'garbage factors found:', factors, 'cofact:', cofact)
                              factors = "Garbage values"
                              tries -= 1
                              if tries == 0:
                                   Print('>'*10 + 'ERROR BAD SEQ MATCH')
                                   error_msg += 'Seq {} had garbage values too many times\n'.format(seq)
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
                                   error_msg += 'Seq {} had no cofactor\n'.format(seq)
                                   return old
                              else:
                                   Print('Seq:', seq, 'no cofactor, retrying ({} tries left) factors: {}'.format(tries, factors))
                              sleep(5)
                              continue
                         elif cofact < 65: # Small cofactor, FDB will auto-factor it
                              tries -= 1
                              if tries == 0:
                                   Print('>'*10 + 'ERROR SMALL COFACTOR')
                                   error_msg += 'Seq {} had a small cofactor\n'.format(seq)
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
                              ali.index += broken[old.seq][1]
                              ali.progress += broken[old.seq][1]
                         if ali.progress <= 0: ali.progress = id_created(ali.id)
                    else: # No 'Resources', no 'Not all factors known'
                         Print('Seq:', seq, 'Strange. Termination? More likely a bad sequence.')
                         ali.factors = "Reportedly terminated"
                         ali.guide, ali.clas, ali.driver = 'Terminated?', -5, True
                         ali.progress = 'Terminated?'
                         error_msg += 'Supposedly, seq {} has terminated!!!'.format(seq)
                    return ali
          else: # Reached query limit
               Print('Seq:', seq, 'the DB is refusing requests.')
               reqs = re.search('bgcolor="#DDDDDD">Page requests</td>\n<td align="center" bgcolor="#DDDDDD">([0-9,]+)</td>',
                    page).group(1)
               queries = re.search('bgcolor="#DDDDDD">Database queries</td>\n<td align="center" bgcolor="#DDDDDD">([0-9,]+)</td>',
                    page).group(1)
               when = re.search('bgcolor="#DDDDDD">Counting since</td>\n<td align="center" bgcolor="#DDDDDD">(.*?)</td>',
                    page).group(1)
               Print(reqs, 'page requests,', queries, 'db queries since', when)
               error_msg += 'Reached query limit. Derp.\n'

while True: # This means you can start it once and leave it, but by setting loop = False you can make it one-and-done
     print('\n'+strftime(datefmt))     
     if special:
          this = special
     else:
          this, start = current_update(per_hour)
     reserves, updated = get_reservations()
     data, oldinfo = get_old_info(JSON, reserves, this, drop)
     Print('Init complete, starting FDB queries')

     count = 0
     for old in oldinfo: # Loop over every sequence to be updated
          if quitting:
               data.append(old)
               continue
          ali = check(old)
          if ali: 
               data.append(ali)
               if not quitting: 
                    count += 1
                    Print(count, 'sequences complete:', old.seq)
          sleep(1)

     with open(template, 'r') as f: # Read in webpage templates
          html = f.read()
     with open(template2, 'r') as f:
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

     html = html.format(updated) # Imbue the template with the reservation time
     
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
     with open(FILE, 'w') as f:
          f.write(html)
     with open(TXT, 'w') as f:
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
          if count != per_hour and start != 0:
               error_msg += 'Something went wrong. Only {} seqs were updated.\n'.format(count)
          Print("Next start is", start)
          with open(sys.argv[0]+'.conf', 'w') as conf: # Save how many sequences we updated
               conf.write(str(start)+'\n')
     
     if error_msg:
          try:
               email('Aliquot failure!', error_msg)
          except Exception as e:
               Print('Email failed:', e)
               Print('Message:', error_msg)

     Print('Written HTML and saved state.')
     
     if not quitting and loop:
          Print('Sleeping.')
          sleeping = True
          sleep(sleep_time)
          sleeping = False
     else: sys.exit()
