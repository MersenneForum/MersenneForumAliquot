#! /usr/bin/python3

# Run from a cron file like "reservations.py spider" however often to parse
# the MF thread and update its head post. Be sure the dir, username and password 
# are set correctly.
# The very first run only checks the most recent page of reservation posts, since
# there isn't yet a record of last post checked

import sys, _import_hack # _import_hack assumes that the numtheory package is in the parent directory of this directory
			 # this should be removed when proper pip installation is supported (and ad hoc python scripts are no longer necessary)

from sequence import Sequence

reservation_page = 'http://www.mersenneforum.org/showpost.php'
res_posts = (165249, 397318, 397319, 397320, 397912, 416583, 416585, 416586) # Tuple to be expanded as necessary
use_local_reservations = False

dir = '.' # Set this appropriately
resfile = dir+'/reservations'
bup = dir+'/backup'
pid_file = dir+'/last_pid'
info = dir+'/AllSeq.txt'

username = 'Dubslow'
passwd = '<nope>'
txtfiles = {'yoyo@home': 'http://yafu.myfirewall.org/yafu/download/ali/ali.txt.all'}
template = """[B]For newcomers:[/B] Please post reservations here. There are workers that extend aliquot sequences; reservations here flag the workers off a sequence so no effort is wasted.
 
For an archive of old reservations, click [URL="http://www.mersenneforum.org/showthread.php?t=14330"]here[/URL].
 
For current driver/guide info, click [URL="http://rechenkraft.net/aliquot/AllSeq.html"]here[/URL].
 
Current reservations:
[code][B]   Seq  Who             Index  Size  [/B]
{}
[/code]
"""

secondary_template = """This post has been hijacked for additional reservations.

[code][B]   Seq  Who             Index  Size  [/B]
{}
[/code]
"""
email_msg = ''

###############################################################################

from myutils import linecount, Print, strftime, blogotubes, add_cookies, email
import re
from time import time

# Some slight modifications of the default global variables

if 'http' in info:
     txt = blogotubes(info)
     if txt is None:
          Print("Couldn't get info, no info will be updated")
          info = None
     else:
          info = dir+'/AllSeq.txt'
          with open(info, 'w') as f:
               f.write(txt)

def get_reservations(pid):
     # Copied from allseq.py
     page = blogotubes(reservation_page + '?p='+str(pid))
     # Isolate the [code] block with the reservations
     page = re.search(r'<pre.*?>(.*?)</pre>', page, flags=re.DOTALL).group(1)
     ind = page.find('\n')
     if ind == -1: # No newline means only "<b>Seq Who Index Size</b>", i.e. empty, so no reservations
          return ""
     else:
          return page[ind+1:] # Dump the first line == "<b>Seq Who Index Size</b>"

if res_posts and not use_local_reservations: 
     reservations = '\n'.join(data for data in map(get_reservations, res_posts) if data)
     try:
          with open(resfile, 'r') as f:
               local_data = f.read()
     except:
          with open(resfile, 'w') as f:
               f.write(reservations)
     else:
          if local_data.strip() != reservations.strip():
               Print("Warning: local file and forum post do not match!")
               Print("Continuing using forum data, local changes are being lost!")
               with open(resfile, 'w') as f:
                    f.write(reservations)

################################################################################
# Begin function definitions, the remaining top-level logic is at the very bottom

def read_db(file=resfile):
     db = {}
     with open(file, 'r') as f:
          for line in f:
               l = line.split()
               seq = Sequence()
               try:
                    seq.seq = int(l[0])
               except ValueError:
                    if l[0] == 'Richard':
                         continue
                    else:
                         raise
               try:
                    seq.index = int(l[-2])
                    seq.size = int(l[-1])
               except ValueError: # Some lines have no data, only <seq name>
                    seq.res = ' '.join(l[1:])
                    try:
                         if info:
                              seq.index, seq.size = get_info(seq.seq)
                    except TypeError:
                         Print(seq.seq, "doesn't exist!")
                         continue
               else:
                    seq.res = ' '.join(l[1:-2])
               db[seq.seq] = seq
     Print("Read {} seqs".format(len(db)))
     return db

def write_db(db, file=resfile):
     c = 0
     with open(file, 'w') as f:
          for seq in sorted(db.keys()):
               f.write(db[seq].reservation_string())
               c += 1
     Print("Wrote {} seqs".format(c))

def add_db(db, name, seqs):
     global email_msg
     for seq in seqs:
          if seq in db:
               other = db[seq].res
               if name == other:
                    string = "Warning: {} already owns {}".format(name, seq)
                    Print(string)
                    email_msg += string+'\n'
               else:
                    string = "Warning: seq {} is owned by {} but is trying to be reserved by {}!".format(seq, other, name)
                    Print(string)
                    email_msg += string+'\n'
          else:
               if info:
                    infos = get_info(seq)
                    if not infos:
                         string = "Warning: {} doesn't appear to be in the list".format(seq)
                         Print(string)
                         email_msg += string+'\n'
                    else:
                         db[seq] = Sequence(seq=seq, res=name, index=infos[0], size=infos[1])

def drop_db(db, name, seqs):
     global email_msg
     b = c = len(seqs)
     for seq in seqs:
          try:
               exists = db[seq].res == name
          except KeyError:
               string = "{} is not reserved at the moment".format(seq)
               Print(string)
               email_msg += string+'\n'
               continue
          if exists:
               del db[seq]
               c -= 1
          else:
               string = "Warning: Seq {}: reservation {} doesn't match dropee {}".format(seq, db[seq].res, name)
               Print(string)
               email_msg += string+'\n'

     if c != 0:
          string = "Only {} seqs were removed, {} were supposed to be dropped".format(b-c, b)
          Print(string)
          email_msg += string+'\n'

def get_info(seq, file=info):
     if file is None:
          return None
     with open(file, 'r') as f:
          for line in f:
               l = line.split()
               if int(l[0]) == seq:
                    return int(l[1][:-1]), int(l[3])
     return None # No such seq

def update(info=info):
     db = read_db()
     list = sorted(db.keys())
     c = len(list)
     if info is not None:
          with open(info, 'r') as f:
               i = 0
               for l in [line.split() for line in f]:
                    if int(l[0]) == list[i]:
                         db[list[i]].index, db[list[i]].size = int(l[1][:-1]), int(l[3])
                         i = (i+1)%c
     write_db(db)

from shutil import copy
def backup(f1=resfile, f2=bup):
     copy(f1, f2)

def send(msg=''):
     global email_msg
     with open(resfile, 'r') as f:
          # first res post gets the main template, the rest get the secondary
          size = len(template)
          size_of_seq = 36
          max = 10000 - size_of_seq
          seqs = []
          for seq in f:
               seqs.append(seq)
               size += size_of_seq
               if size > max:
                    break
          body = template.format(''.join(seqs))
          bodies = [body]
          # The rest get the secondary template
          for post in res_posts[1:]:
               seqs = []
               size = len(secondary_template)
               for seq in f:
                    seqs.append(seq)
                    size += size_of_seq
                    if size > max:
                         break
               bodies.append(secondary_template.format(''.join(seqs)))
          size = len(list(f))

     if size > 0:
          string = "Error: {} seqs couldn't fit into the posts".format(size)
          Print(string)
          email_msg += string+'\n'
     else:
          Print("There's room for ~{} more reservations".format( (10000-len(bodies[-1]))//36 ) )
          editor = PostEditor()
          if not editor.is_logged_in():
               string = 'Warning: user is not logged in, the res posts were not edited'
               Print(string)
               email_msg += string+'\n'
               return
          for postid, body in zip(res_posts, bodies):
               if not editor.edit_post(postid, body, 'Autoedit: '+msg):
                    return postid

#from time import time
#from urllib import request, parse, error
#from http.cookiejar import CookieJar
class PostEditor:
     def __init__(self):
          self._logged_in = False
          #request.install_opener(request.build_opener(request.HTTPCookieProcessor(CookieJar())))
          add_cookies()
          self._logged_in = self.login()
          self._time = time()

     def login(self):
          data = {'vb_login_username': username, 'vb_login_password': passwd}
          data['s'] = ''
          data['securitytoken'] = 'guest'
          data['do'] = 'login'
          data['vb_login_md5password'] = ''
          data['vb_login_md5password_utf'] = ''
          data['cookieuser'] = '1'
          page = blogotubes('http://www.mersenneforum.org/login.php?do=login', data=data)
          return username in page

     def is_logged_in(self):
          self._logged_in = (time() - self._time < 300) and self._logged_in # Somewhat arbitrary 5 min timeout
          return self._logged_in

     def fill_form(self, body, postid, stoken, phash, ptime, reason=''):
          data = {}
          url = 'http://www.mersenneforum.org/editpost.php?do=updatepost&amp;p='+postid
          if reason != '':
               if len(reason) > 200:
                    Print("Reason is too long, chop {} chars".format(len(reason)-200))
               else:
                    data['reason'] = reason
          data['title'] = 'Aliquot sequence reservations'
          data['message'] = body
          data['iconid'] = '2' # arrow icon
          data['securitytoken'] = stoken
          data['do'] = 'updatepost'
          data['p'] = postid
          data['posthash'] = phash
          data['poststarttime'] = ptime
          data['sbutton'] = 'Save Changes'

          return data

     def parse_tokens(self, page):
          stoken = re.search(r'<input type="hidden" name="securitytoken" value="([0-9a-f-]*?)" />', page).group(1)
          phash = re.search(r'<input type="hidden" name="posthash" value="([0-9a-f]*?)" />', page).group(1)
          ptime = re.search(r'<input type="hidden" name="poststarttime" value="([0-9]*?)" />', page).group(1)
          return stoken, phash, ptime

     def edit_post(self, postid, body, reason=''):
          if not self.is_logged_in():
               raise ValueError("Failure: can't edit post before logging in")
          postid = str(postid)
          page = blogotubes('http://www.mersenneforum.org/editpost.php?do=editpost&p='+postid)
          if username not in page: # Verify cookies installed properly
               raise ValueError("Failure: tried to edit post {} but not logged in!".format(postid))
          stoken, phash, ptime = self.parse_tokens(page)
          data = self.fill_form(body, postid, stoken, phash, ptime, reason)
          page = blogotubes('http://www.mersenneforum.org/editpost.php?do=updatepost&amp;p='+postid, data=data)
          # Ignore response until I know what to check for
          return page

def spider(last_pid):
     wobsite = 'http://www.mersenneforum.org/showthread.php?t=11588&page='
     backup()
     db = read_db()
     spider_msg = []

     ###############################################################################################
     # First the standalone func that processes mass text file reservations
     def parse_text_file(reservee, url):
          global email_msg
          old = {seq.seq for seq in db.values() if seq.res == reservee}
          txt = blogotubes(url)
          current = set()
          for line in txt.splitlines():
               if re.match(r'(?<![0-9])[0-9]{5,6}(?![0-9])', line):
                    seq = int(line)
                    if seq in current:
                         string = "Duplicate sequence? {} {}".format(seq, url)
                         Print(string)
                         email_msg += string+'\n'
                    else:
                         current.add(seq)
               elif not re.match(r'^[0-9]+$', line):
                    string = "Unknown line from {}: {}".format(url, line)
                    Print(string)
                    email_msg += string+'\n'
          # easy peasy lemon squeezy
          done = old - current
          new = current - old
          if done or new:
               spider_msg.append('{}: Add {}, Drop {}'.format(reservee, len(new), len(done)))
               drop_db(db, reservee, done)
               add_db(db, reservee, new)

     ###############################################################################################
     # This processes the parsed HTML and its add/drop commands, and actually affects the current reservations
     
     def process_msg(pid, name, msg):
          add = []; addkws = ('Reserv', 'reserv', 'Add', 'add', 'Tak', 'tak')
          drop = []; dropkws = ('Unreserv', 'unreserv', 'Drop', 'drop', 'Releas', 'releas')
          for line in msg.splitlines():
               if any(kw in line for kw in dropkws):
                    for s in re.findall(r'(?<![0-9])[0-9]{5,6}(?![0-9])', line): # matches only 5/6 digit numbers
                         drop.append(int(s))
               elif any(kw in line for kw in addkws):
                    for s in re.findall(r'(?<![0-9])[0-9]{5,6}(?![0-9])', line):
                         add.append(int(s))
          la = len(add)
          ld = len(drop)
          if la or ld:
               Print('{}: {} adding {}, dropping {}'.format(pid, name, repr(add), repr(drop)))
               spider_msg.append('{}: Add {}, Drop {}'.format(name, la, ld))
               add_db(db, name, add)
               drop_db(db, name, drop)

     ###############################################################################################
     # Begin the parsers, converts the various HTML into Python data structures for processing
     # Also reverse stack order
     # For each page of the thread, the parsers return a list of (post_id, author, html-replaced-post_body)
     
     # All of my previous html parsing needs have been simple enough that regexs were sufficient,
     # and a proper parser would have been overkill; this, though, is much closer to the border, and if I
     # already knew how to use any parser, I would. But the overhead is too much to start now, so...
     # thankfully there are comments in the html that are individually closed; without that, 
     # this would be substantially harder and I'd probably resort to a parser.     
     def parse_msg(msg):
          # Drop text after the last </div>
          ind = msg.rfind('</div>')
          msg = msg[:ind]
          if msg.count('<div') > 1: # There are quotes in the message
               # drop text before the second to last </div>
               ind = msg.rfind('</div>')
               msg = msg[ind+6:]
          else:
               # drop text after the first tag
               ind = msg.find('>')
               msg = msg[ind+1:]
          return msg.replace('<br />', '').strip()
     
     def parse_post(post):
          name = re.search(r'''alt="(.*?) is o''', post).group(1) # "is offline" or "is online"
          msg = re.search(r'<!-- message -->(.*?)<!-- / message -->', post, re.DOTALL).group(1)
          return name, parse_msg(msg)

     def parse_page(page):
          out = []
          posts = re.findall(r'<!-- post #([0-9]{6,7}) -->(.*?)<!-- / post #\1 -->', page, re.DOTALL)
          for post in posts:
               #name, msg = parse_post(post[1])
               out.append(  (int(post[0]),) + parse_post(post[1])  )
          return out

     #################################################################################################
     # End parsers, first one tiny helper function

     def order_posts(posts):
          if posts != sorted(posts, key=lambda post: post[0]):
               raise ValueError("Out of order posts! Pids:\n{}".format([post[0] for post in posts]))
          return posts[0][0]

     #################################################################################################
     # Now begin actual logic of top-level spider()

     html = blogotubes(wobsite+'10000') # vBulletin rounds to last page
     all_pages = [parse_page(html)]
     lowest_pid = order_posts(all_pages[0])
     if not last_pid: # If this is the first time running the script
          last_pid = lowest_pid # On first time run, ignore all but the last page
     while lowest_pid > last_pid: # It's probable that we missed some posts on previous page
          page_num = re.search('<td class="vbmenu_control" style="font-weight:normal">Page ([0-9]+)', html).group(1)
          page_num = str(int(page_num)-1)
          Print("Looks like posts were missed, checking page", page_num)
          html = blogotubes(wobsite+page_num)
          all_pages.insert(0, parse_page(html))
          lowest_pid = order_posts(all_pages[0])

     all_posts = [post for page in all_pages for post in page if post[0] > last_pid]
     if all_posts:
          order_posts(all_posts) # Assert order, ignore lowest pid retval
          for post in all_posts:
               process_msg(*post)
          last_pid = all_posts[-1][0] # Highest PID processed
     else:
          Print("No new posts!")

     for reservee, url in txtfiles.items():
          parse_text_file(reservee, url)

     if spider_msg:
          write_db(db)
          update()
          if not use_local_reservations:
               send('Spider: ' + ' | '.join(spider_msg)) # For now, doesn't check if send was successful

     return last_pid

#######################################################################################################
# End of all function definitions

if __name__ == '__main__':
     err = "Error: commands are 'add', 'drop', 'send', 'update', 'print', or 'spider'"
     from sys import argv, exit
     if len(argv) < 2:
          print(err)
          exit(-1)
     if argv[1] == 'send':
          if len(argv[2:]) < 1: argv.append('')
          send(' '.join(argv[2:]))
     elif argv[1] == 'add':
          backup()
          db = read_db()
          if len(argv[2:]) < 2:
               Print("Error: {} add <name> <seq> [<seq>...]".format(argv[0]))
          else:
               Print("Add {} seqs".format(len(argv[3:])))
               add_db(db, argv[2], [int(seq.replace(',','')) for seq in argv[3:]])
          write_db(db)
     elif argv[1] == 'drop':
          backup()
          db = read_db()
          if len(argv[2:]) < 2:
               Print("Error: {} add <name> <seq> [<seq>...]".format(argv[0]))
          else:
               Print("Drop {} seqs".format(len(argv[3:])))
               drop_db(db, argv[2], [int(seq.replace(',','')) for seq in argv[3:]])
          write_db(db)
     elif argv[1] == 'print':
          write_db(read_db())
          with open(resfile, 'r') as f:
               for line in f:
                    print(line, end='') # Line newline + print newline = extra whitespace
     elif argv[1] == 'update':
          update()
     elif argv[1] == 'spider':
          try:
               with open(pid_file, 'r') as f:
                    last_pid = int(f.read())
          except FileNotFoundError:
               last_pid = None
          last_pid = spider(last_pid)
          with open(pid_file, 'w') as f:
               f.write(str(last_pid) + '\n')
     else:
          print(err)
          exit(-1)
     if email_msg:
          try:
               email('Reservations script warnings', email_msg)
          except Exception as e:
               Print('Email failed:', e)
               Print('Message:\n', email_msg)
