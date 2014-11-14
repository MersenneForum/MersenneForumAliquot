#! /usr/bin/python3

# Run from a cron file like "reservations.py spider" however often to parse
# the MF thread and update its head post. Be sure the dir, username and password 
# are set correctly.
# Before the very first run (and only before it) put the current last post ID
# (should be in the 300K area) into the pid_file specified below. The script will
# update it as necessary.


dir = '.' # Set this appropriately
resfile = 'http://mersenneforum.org/showpost.php?p=165249'
bup = dir+'/backup'
pid_file = dir+'/last_pid'
info = 'http://dubslow.tk/aliquot/AllSeq.txt'
username = 'Dubslow'
passwd = '<nope>'
template = """[B]For newcomers:[/B] Please post reservations here. There are workers that extend aliquot sequences; reservations here flag the workers off a sequence so no effort is wasted.
 
For an archive of old reservations, click [URL="http://www.mersenneforum.org/showthread.php?t=14330"]here[/URL].
 
For current driver/guide info, click [URL="http://dubslow.tk/aliquot/AllSeq.html"]here[/URL].
 
Current reservations:
[code][B]   Seq  Who             Index  Size  [/B]
{}
[/code]
"""

from myutils import linecount, Print, strftime, blogotubes, add_cookies
import re

if 'http' in info:
     txt = blogotubes(info)
     if txt is None:
          print("Couldn't get info, no info will be updated")
          info = None
     else:
          info = dir+'/AllSeq.txt'
          with open(info, 'w') as f:
               f.write(txt)

if 'http' in resfile: 
     # Copied from allseq.py
     page = blogotubes('http://www.mersenneforum.org/showpost.php?p=165249')
     # Isolate the [code] block with the reservations
     page = re.search(r'<pre.*?>(.*?)</pre>', page, flags=re.DOTALL).group(1)
     ind = page.find('\n')
     page = page[ind+1:] # Dump the first line
     resfile = dir+'/reservations'
     with open(resfile, 'w') as f:
          f.write(page)     

class Sequence:
     def __init__(self, seq=0, name=None, index=0, size=0):
          self.seq = seq
          self.size = size
          self.index = index
          self.name = name
     
     def __str__(self):
          #   966  Paul Zimmermann   893  178
          #933436  unconnected     12448  168
          out = "{:>6d}  {:15s} {:>5d}  {:>3d}\n".format(self.seq, self.name, self.index, self.size)
          if 'jacobs and' in self.name:
               out += '        Richard Guy\n'
          return out

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
                    seq.name = ' '.join(l[1:])
                    try:
                         seq.index, seq.size = get_info(seq.seq)
                    except TypeError:
                         Print(seq.seq, "does'nt exist!")
                         continue
               else:
                    seq.name = ' '.join(l[1:-2])
               db[seq.seq] = seq
     print("Read {} seqs".format(len(db)))
     return db

def write_db(db, file=resfile):
     c = 0
     with open(file, 'w') as f:
          for seq in sorted(db.keys()):
               f.write(str(db[seq]))
               c += 1
     print("Wrote {} seqs".format(c))

def add_db(db, name, seqs):
     for seq in seqs:
          info = get_info(seq)
          if not info:
               print("Warning: seq", seq, "doesn't appear to be in the list")
          else:
               db[seq] = Sequence(seq, name, *info)

def drop_db(db, name, seqs):
     b = c = len(seqs)
     for seq in seqs:
          try:
               exists = db[seq].name == name
          except KeyError:
               print("{} is not reserved at the moment".format(seq))
               continue
          if exists:
               del db[seq]
               c -= 1
          else:
               print("Warning: Seq {}: reservation {} doesn't match dropee {}".format(seq, db[seq].name, name))

     if c != 0:
          print("Only {} seqs were removed, {} were supposed to be dropped".format(b-c, b))

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
     with open(resfile, 'r') as f:
          seqs = f.read()
     body = template.format(seqs)
     size = len(body)
     if size >= 10000:
          print("Error: post size = {} is too large".format(size))
     else:
          print("There's room for ~{} more reservations".format( (10000-size)//35 ) )
          edit_post(165249, body, 'Autoedit: '+msg)

def edit_post(postid, body, reason=''):
     postid = str(postid)
     #from urllib import request, parse, error
     #from http.cookiejar import CookieJar
     def login():
          data = {'vb_login_username': username, 'vb_login_password': passwd}
          data['s'] = ''
          data['securitytoken'] = 'guest'
          data['do'] = 'login'
          data['vb_login_md5password'] = ''
          data['vb_login_md5password_utf'] = ''
          data['cookieuser'] = '1'
          #print('cookies?')
          page = blogotubes('http://www.mersenneforum.org/login.php?do=login', data=data)
          return username in page

     def fill_form(body, postid, stoken, phash, ptime, reason=''):
          data = {}
          url = 'http://www.mersenneforum.org/editpost.php?do=updatepost&amp;p='+postid
          if reason != '':
               if len(reason) > 200:
                    print("Reason is too long, chop {} chars".format(len(reason)-200))
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

     def parse_tokens(page):
          import re
          stoken = re.search(r'<input type="hidden" name="securitytoken" value="([0-9a-f-]*?)" />', page).group(1)
          phash = re.search(r'<input type="hidden" name="posthash" value="([0-9a-f]*?)" />', page).group(1)
          ptime = re.search(r'<input type="hidden" name="poststarttime" value="([0-9]*?)" />', page).group(1)
          return stoken, phash, ptime

     #request.install_opener(request.build_opener(request.HTTPCookieProcessor(CookieJar())))
     add_cookies()
     if not login():
          print("Failure 1")
          return
     page = blogotubes('http://www.mersenneforum.org/editpost.php?do=editpost&p='+postid)
     if username not in page: # Verify cookies installed properly
          print("Failure 2")
          return
     stoken, phash, ptime = parse_tokens(page)
     data = fill_form(body, postid, stoken, phash, ptime, reason)
     page = blogotubes('http://www.mersenneforum.org/editpost.php?do=updatepost&amp;p='+postid, data=data)
     # Ignore response until I know what to check for
     return page

def spider(last_pid):
     wobsite = 'http://www.mersenneforum.org/showthread.php?t=11588&page='
     backup()
     db = read_db()
     spider_msg = []
     
     def process_msg(pid, name, msg):
          add = []
          drop = []
          for line in msg.splitlines():
               if 'R' in line or 'A' in line or 'T' in line:
                    for s in re.findall(r'(?<![0-9])[0-9]{5,6}(?![0-9])', line): # matches only 5/6 digit numbers
                         add.append(int(s))
               elif 'U' in line or 'D' in line:
                    for s in re.findall(r'(?<![0-9])[0-9]{5,6}(?![0-9])', line):
                         drop.append(int(s))
          la = len(add)
          ld = len(drop)
          if la or ld:
               Print('{}: {} adding {}, dropping {}'.format(pid, name, repr(add), repr(drop)))
               spider_msg.append('{}: Add {}, Drop {}'.format(name, la, ld))
               add_db(db, name, add)
               drop_db(db, name, drop)
          
     def process_page(posts, last_pid):
          lowest_pid = posts[0][0]
          highest_pid = posts[-1][0]
          for post in posts:
               pid = post[0]
               if pid < lowest_pid: # Since they are processed in order, this shouldn't happen...
                    Print("Found an out of order PID! {}, {}".format(lowest_pid, pid))
                    lowest_pid = pid
               if pid > highest_pid: # This OTOH should always be true
                    highest_pid = pid 
               if pid > last_pid:
                    process_msg(*post)
          return lowest_pid, highest_pid
     
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
               out.append((int(post[0]),) + parse_post(post[1]))
          return out
     
     page = blogotubes(wobsite+'10000') # vBulletin rounds to last page
     lowest_pid, highest_pid = process_page(parse_page(page), last_pid)
     while lowest_pid > last_pid: # It's probable that we missed some posts on previous page
          page_num = re.search('<td class="vbmenu_control" style="font-weight:normal">Page ([0-9]+)', page).group(1)
          page_num = str(int(page_num)-1)
          Print("Checking page", page_num)
          page = blogotubes(wobsite+page_num)
          lowest_pid, tmp = process_page(parse_page(page), last_pid)
          if tmp > highest_pid: # should never happen
               Print("WTF? {}, {}".format(tmp, highest_pid))
               highest_pid = tmp
     if spider_msg:
          update()
          write_db(db)
          send('Spider: ' + ' | '.join(spider_msg))
     return highest_pid

if __name__ == '__main__':
     from sys import argv
     if argv[1] == 'send':
          if len(argv[2:]) < 1: argv.append('')
          send(' '.join(argv[2:]))
     elif argv[1] == 'add':
          backup()
          db = read_db()
          if len(argv[2:]) < 2:
               print("Error: {} add <name> <seq> [<seq>...]".format(argv[0]))
          else:
               print("Add {} seqs".format(len(argv[3:])))
               add_db(db, argv[2], [int(seq.replace(',','')) for seq in argv[3:]])
          write_db(db)
     elif argv[1] == 'drop':
          backup()
          db = read_db()
          if len(argv[2:]) < 2:
               print("Error: {} add <name> <seq> [<seq>...]".format(argv[0]))
          else:
               print("Drop {} seqs".format(len(argv[3:])))
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
          with open(pid_file, 'r') as f:
               last_pid = int(f.read())
          last_pid = spider(last_pid)
          with open(pid_file, 'w') as f:
               f.write(str(last_pid) + '\n')
     else:
          print("Error: commands are 'add', 'drop', 'send', 'update', 'print', or 'spider'")
