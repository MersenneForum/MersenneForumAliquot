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
SEQLIST = dir + 'SeqList.txt'
STATEFILE = sys.argv[0] + '.conf'
LOCKFILE = sys.argv[0] + '.lock'
DATEFMT = '%Y-%m-%d %H:%M:%S'


#RESPAGE = 'http://www.mersenneforum.org/showpost.php'
#RESPOSTIDS = (165249, 397318, 397319, 397320, 397912, 416583, 416585, 416586)
RESPAGE = 'http://www.rechenkraft.net/aliquot/res_post.php'
RESPOSTIDS = (1,)


BATCHSIZE = 110
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
from mfaliquot.sequence import AliquotSequence

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

###############################################################################
# Functions relating to to reading/writing SEQLIST and STATEFILE, including do_drops()

def read_state():
     try:
          with open(STATEFILE, 'r') as conf: # Read which sequences to update
               start = int(conf.readline())
     except FileNotFoundError as e:
          Print('State file not found, starting from sequence 0')
          start = 0
     return start


def write_state(state):
     with open(STATEFILE, 'w') as conf: # Save how many sequences we updated
          conf.write(str(state)+'\n')


def read_seqlist():
     with open(SEQLIST, 'r') as f:
          return list(int(line) for line in f)


def write_seqlist(seqlist):
     with open(SEQLIST, 'w') as f:
          for seq in seqlist:
               f.write(str(seq)+'\n')


def read_and_parse_data():
     with open(JSON, 'r') as f:
          olddat = json.load(f)['aaData']
     data_dict = {}
     for dat in olddat:
          ali = AliquotSequence(lst=dat)
          data_dict[ali.seq] = ali
     return data_dict


def write_data(data_dict):
     ali_list = list(data_dict.values())
     ali_list.sort(key=lambda ali: ali.seq)

     json_string = json.dumps({"aaData": ali_list}).replace('],', '],\n')+'\n'
     with open(JSON, 'w') as f:
          f.write(json_string)

     txt_string = '\n'.join(str(ali) for ali in ali_list)
     with open(ASTXT, 'w') as f:
          f.write(txt_string+'\n')


def do_drops(drops):
     '''Returns (succesful drops, failed drops, seqlist_total). Updates SEQLIST.
     Direct data files are updated, html/stats are not.
     BE CERTAIN THE DATA FILES ARE UP TO DATE BEFORE CALLING.'''
     global ERRORMSG
     seqlist = read_seqlist()
     data_dict = read_and_parse_data()

     drops = set(drops)
     seqlist_set = set(seqlist)
     data_dict_set = set(data_dict.keys())

     seqlist_drops = drops & seqlist_set
     data_drops = drops & data_dict_set

     for d in seqlist_drops:
          seqlist.remove(d)

     for d in data_drops:
          del data_dict[d]

     drops -= seqlist_drops
     drops -= data_drops

     if drops:
          Print("These seqs were in neither seqlist nor data, ignored: {}".format(drops))
          ERRORMSG += "These seqs were in neither seqlist nor data, ignored: {}\n".format(drops)

     write_seqlist(seqlist)
     write_data(data_dict)

     if seqlist_drops:
          Print("Dropped {} seqs from seq_list: {}".format(len(seqlist_drops), seqlist_drops))
     if data_drops:
          Print('Dropped {} seqs from datadict: {}'.format(len(data_drops), data_drops))

     extra_data = data_dict_set - seqlist_set
     if extra_data:
          Print("Warning: found seqs in data that aren't in seqlist; should they be automatically removed? {}".format(extra_data))
          ERRORMSG += "Warning: found seqs in data that aren't in seqlist; should they be automatically removed? {}\n".format(extra_data)

     return seqlist_drops, data_drops, len(seqlist)


def get_reservations():
     reserves = {}
     for pid in RESPOSTIDS:
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

###############################################################################

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
     out = [ int(t[1:]) for t in [t.strip() for t in s.split('*')] if t[0] == 'C' ]
     # forall stripped sections of s separated by '*': if the first character is 'C', return the int in the rest of the section
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


###############################################################################
# WOULD YOU LIKE SOME MEATBALLS WITH THIS SPAGHETTI?

def check(old, tries=3, reserves=None, special=None):
     if tries <= 0:
          Print('Bad sequence or id! Seq:', old.seq)
          return old
     if not old or not old.is_valid() or not old.id or special:
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
                    ali = AliquotSequence(seq=seq, size=int(info.group('size')), index=int(info.group('index')), id=int(info.group('id')))
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
                         ERRORMSG += 'Supposedly, seq {} has terminated!!!\n'.format(seq)
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
                    Print("{} page reqs, {} new ids, {} db queries, {}s cpu time since {}".format(pages, ids, queries, cputime, when))
               except AttributeError: # some re.search() failed
                    Print('Not only is it refusing requests, but its formatting has changed!')
               QUITTING = True
               return old

# End spaghetti... hopefully
###############################################################################
# Begin the family of "main" functions: first the main_helpers

def main_initialize(special=None):
     seqlist = read_seqlist()

     if special:
          seqs_todo = special
          start = None
     else:
          start = read_state()
          Print('Start:', start)
          seqs_todo = seqlist[start: (start + BATCHSIZE)]

     if TODROP:
          seqlist_drops, _data_drops, _seqlist_len = do_drops(TODROP)
          for d in seqlist_drops.intersection(seqs_todo):
               seqs_todo.remove(d)
          # We get seqs_todo *before* doing drops to ensure that `start` is accurate (otherwise possible that some seqs get skipped)
          seqlist = read_seqlist()

     # After seqlist is done, get data and update reservations
     data_dict = read_and_parse_data()
     reservations, reservations_time = get_reservations()
     for seq, res in reservations.items():
          if seq in data_dict: # If reservations are out of date
               data_dict[seq].res = res

     # Check for garbage and/or new sequences
     newseqs = []
     for seq in seqs_todo:
          ali = data_dict.get(seq, None)
          if not ali:
               data_dict[seq] = AliquotSequence(seq=seq, index=-1)
               if seq not in seqlist:
                    if seq <= 276 or seq >= 10**7 or not seq & 1 == 0:
                         del data_dict[seq]
                         raise ValueError("Can't add sequence {}".format(seq))
                    seqlist.append(seq)
                    newseqs.append(seq)
     if newseqs:
          write_seqlist(seqlist)
          Print('Added {} new sequences: {}'.format(len(newseqs), newseqs))

     seqlist_total = len(seqlist)
     #print(start, seqs_todo)

     return seqs_todo, start, seqlist_total, data_dict, reservations, reservations_time


def find_merges(data_dict):
     ids = {}
     merged = []
     for ali in data_dict.values():
          this = ali.id
          try:
               other = ids[this]
          except KeyError: # No match for this id
               ids[this] = ali.seq # this id is the tail of this seq
          else: # found a match (i.e. a merge)
               seq = ali.seq
               if seq > other:
                    pair = seq, other
               else:
                    pair = other, seq
               merged.append(pair)

     if merged:
          Print('Found merges!')
          for merge in merged:
               Print('{} seems to have merged with {}'.format(*merge))
          try:
               email('Aliquot merge!', '\n'.join('{} seems to have merged with {}'.format(*merge) for merge in merged))
          except Exception as e:
               Print("alimerge email failed")

          drops = [merge[0] for merge in merged]
          _, _, seqlist_total = do_drops(drops)

          return seqlist_total

     else:
          Print("No merges found")
          return None


def create_stats_write_html(data_dict, reservations_time):
     # Now get all the stats (i.e. count all the instances of stuff)
     # It's a bit long, tedious and ugly, but I don't think there's anything for it
     sizes = Counter(); lens = Counter(); guides = Counter(); progs = Counter(); cofacts = Counter()
     totsiz = 0; totlen = 0; avginc = 0; totprog = 0
     for ali in data_dict.values():
          sizes[ali.size] += 1; totsiz += ali.size
          lens[ali.index] += 1; totlen += ali.index
          guides[ali.guide] += 1; avginc += ali.index/ali.size
          progs[ali.progress] += 1
          cofacts[ali.cofact] += 1

          if isinstance(ali.progress, int):
               totprog += 1

     # Create broken sequences HTML
     if BROKEN:
          # horizontal table: create a list of tuples containing each column (i.e. each sequence)
          entries = (('''<a href="http://factordb.com/sequences.php?se=1&aq={}&action=last20">{}</a>'''.format(BROKEN[seq][1], seq), str(BROKEN[seq][0])) for seq in sorted(BROKEN))
          row1, row2 = zip(*entries)
          r1 = ''.join('<td>{}</td>'.format(datum) for datum in row1)
          r2 = ''.join('<td>{}</td>'.format(datum) for datum in row2)
          borken_html = '<table><tr><th scope="row">Sequence</th>{}</tr><tr><th scope="row">Index offset</th>{}</tr></table>'.format(r1, r2)
          unborken_html = ''
     else:
          borken_html = ''
          unborken_html = 'none currently.'

     # Read in webpage templates
     with open(TMPLT, 'r') as f:
          html = f.read()
     with open(STATSTMPLT, 'r') as f:
          stats = f.read()

     html = html.format(reservations_time, unborken_html, borken_html) # Imbue the template with the reservation time and broken sequences

     # Put stats table in json-able format
     data_total = len(data_dict)
     lentable = []; lencount = 0
     sizetable = [ [key, value] for key, value in sizes.items() ]
     cofactable = [ [key, value] for key, value in cofacts.items() ]
     for leng, cnt in sorted(lens.items(), key=lambda tup: tup[0]):
          lentable.append( [leng, cnt, "{:2.2f}".format(lencount/(data_total-cnt)*100)] )
          lencount += cnt
     guidetable = [ [key, value] for key, value in guides.items() ]
     progtable = [ [key, value] for key, value in progs.items() ]
     stats = stats.format(totinc=totlen/totsiz, avginc=avginc/data_total, totprog=totprog, progcent=totprog/data_total)

     # Write the statsdata and webpages
     with open(ASHTML, 'w') as f:
          f.write(html)
     with open(STATS, 'w') as f:
          f.write(stats)
     with open(STATSON, 'w') as f:
          f.write(json.dumps({"aSizes": sizetable, "aCofacts": cofactable, "aGuides": guidetable, "aProgress": progtable, "aLens": lentable}).replace('],', '],\n')+'\n')


def main_finalize(special, start, count, supposed_to, seqlist_total):
     global ERRORMSG

     if not special:
          start += count
          if start >= seqlist_total:
               start = 0
          if count != supposed_to and start != 0:
               ERRORMSG += 'Something went wrong. Only {} seqs were updated.\n'.format(count)
          Print("Next start is", start)
          write_state(start)

     if ERRORMSG:
          try:
               email('Aliquot failure!', ERRORMSG)
          except Exception as e:
               Print('Email failed:', e)
               Print('Message:\n', ERRORMSG)


# End main helpers
###############################################################################
# Begin actual mains()

def inner_main(special=None):
     global ERRORMSG
     print('\n'+strftime(DATEFMT))
     Print('Initializing')

     seqs_todo, start, seqlist_total, data_dict, reservations, reservations_time = main_initialize(special)
     Print('Init complete, starting FDB queries')

     # Main loop
     count = 0
     for seq in seqs_todo:
          ali = check(data_dict[seq], reserves=reservations, special=special)

          if not ali or not ali.is_valid():
               del data_dict[seq]
          data_dict[seq] = ali

          if QUITTING:
               break

          count += 1
          Print('{} sequence{} complete: {}'.format(count, 's' if count > 1 else ' ', ali.seq))
          sleep(1)

     write_data(data_dict)
     Print('Loop complete, new data saved')

     tmp = find_merges(data_dict) # might call do_drops, so refresh data for stats
     if tmp:
          seqlist_total = tmp
          data_dict = read_and_parse_data()

     create_stats_write_html(data_dict, reservations_time)
     Print('Written all data and HTML')

     main_finalize(special, start, count, len(seqs_todo), seqlist_total)
     Print('Saved state and finalized.')


################################################################################
# Start actual code execution

def main():
     if os.path.exists(LOCKFILE):
          Print("Didn't start: lockfile is present")
          sys.exit(-1)

     global LOOPING, SLEEPING

     try:
          special = {int(arg) for arg in sys.argv[1:]}
     except ValueError:
          print('Error: Args are sequences to be run')
          sys.exit(-1)

     if special:
          LOOPING = False
     else:
          special = None

     # This means you can start it once and leave it, but by setting LOOPING = False you can make it one-and-done
     # This would be a good place for a do...while syntax
     while True:
          open(LOCKFILE, 'a').close()

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
