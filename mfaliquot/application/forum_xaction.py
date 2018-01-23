# This is written to Python 3.6 standards
# indentation: 5 spaces (eccentric personal preference)
# when making large backwards scope switches (e.g. leaving def or class blocks),
# use two blank lines for clearer visual separation

#    Copyright (C) 2014-2017 Bill Winslow
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

# This file contains the code to spider the reservations thread, and later down
# some no longer used legacy code to update the res posts in the thread. That
# code is not maintained.


import re, logging
from .. import blogotubes


_logger = logging.getLogger(__name__)
SEQ_REGEX = re.compile(r'(?<![0-9])[0-9]{5,7}(?![0-9])') # matches only 5-7 digit numbers

################################################################################
# Spidering/reading code
#

# This is the top level function that spiders the thread
def spider_res_thread(last_pid):
     wobsite = 'http://www.mersenneforum.org/showthread.php?t=11588&page='

     html = blogotubes(wobsite+'100000') # vBulletin rounds to last page
     if not html:
          _logger.error(f"unable to spider forum")
          return last_pid, [], []
     all_pages = [_parse_page(html)]
     lowest_pid = _order_posts(all_pages[0])

     if not last_pid: # If this is the first time running the script
          last_pid = lowest_pid # On first time run, ignore all but the last page

     prev_pages = []
     while lowest_pid > last_pid: # It's probable that we missed some posts on previous page
          page_num = re.search('<td class="vbmenu_control" style="font-weight:normal">Page ([0-9]+)', html).group(1)
          page_num = str(int(page_num)-1)
          _logger.info("forum_spider: looks like posts were missed, checking page {}".format(page_num))
          prev_pages.append(page_num)
          html = blogotubes(wobsite+page_num)
          if not html:
               _logger.error(f"unable to spider forum (prev page)")
               return last_pid, [], []
          all_pages.insert(0, _parse_page(html))
          lowest_pid = _order_posts(all_pages[0])

     all_posts = [post for page in all_pages for post in page if post[0] > last_pid]
     all_res = []
     if all_posts:
          _order_posts(all_posts) # Assert order, ignore lowest pid retval
          for pid, name, msg in all_posts:
               adds, drops, updates = _read_msg(msg)
               if adds or drops or updates:
                    _logger.info(f'post id {pid}: {name} adding {adds}, dropping {drops}, updating {updates}')
               all_res.append((name, adds, drops, updates))
          last_pid = all_posts[-1][0] # Highest PID processed
     else:
          _logger.info("no new res thread posts!")

     return last_pid, prev_pages, all_res


# This processes the parsed HTML and its add/drop commands
def _read_msg(msg):
     '''This processes the parsed HTML and its add/drop commands. Returns the two
     such list of sequences.'''
     add = []; addkws = ('Reserv', 'reserv', 'Add', 'add', 'Tak', 'tak')
     drop = []; dropkws = ('Unreserv', 'unreserv', 'Drop', 'drop', 'Releas', 'releas')
     update = []; updatekws = ('Update', 'update')

     for line in msg.splitlines():
          if any(kw in line for kw in dropkws):
               for s in SEQ_REGEX.findall(line):
                    drop.append(int(s))
          elif any(kw in line for kw in addkws):
               for s in SEQ_REGEX.findall(line):
                    add.append(int(s))
          elif any(kw in line for kw in updatekws):
               for s in SEQ_REGEX.findall(line):
                    update.append(int(s))

     return tuple(add), tuple(drop), tuple(update)


# Begin the parsers, converts the various HTML into Python data structures for processing
# Also reverse stack order
# For each page of the thread, the parsers return a list of (post_id, author, html-replaced-post_body)

# All of my previous html parsing needs have been simple enough that regexs were sufficient,
# and a proper parser would have been overkill; this, though, is much closer to the border, and if I
# already knew how to use any parser, I would. But the overhead is too much to start now, so...
# thankfully there are comments in the html that are individually closed; without that,
# this would be substantially harder and I'd probably resort to a parser.
def _parse_msg(msg):
     # Drop text after the last </div>
     ind = msg.rfind('</div>')
     msg = msg[:ind]
     if msg.count('<div') > 1: # There are quotes in the message
          # drop text before the second to last </div>
          ind = msg.rfind('</div>')
          msg = msg[ind+6:]
     else:
          # drop text after the first tag
          # ^^ this comment doesn't match the code?
          ind = msg.find('>')
          msg = msg[ind+1:]
     return msg.replace('<br />', '').strip()


def _parse_post(post):
     name = re.search(r'''alt="(.*?) is o''', post).group(1) # "is offline" or "is online"
     msg = re.search(r'<!-- message -->(.*?)<!-- / message -->', post, re.DOTALL).group(1)
     return name, _parse_msg(msg)


def _parse_page(page):
     '''returns a list of (pid, name, msg)s'''
     out = []
     posts = re.findall(r'<!-- post #([0-9]{6,7}) -->(.*?)<!-- / post #\1 -->', page, re.DOTALL)
     for post in posts:
          #name, msg = parse_post(post[1])
          out.append(  (int(post[0]),) + _parse_post(post[1])  )
     return out


# End parsers, one tiny helper function for spider_forum()
def _order_posts(posts):
     if posts != sorted(posts, key=lambda post: post[0]):
          raise ValueError("Out of order posts! Pids:\n{}".format([post[0] for post in posts]))
     return posts[0][0]


################################################################################

################################################################################

################################################################################
# The stuff here is used to edit the forum posts holding the reservations list,
# but is not used. It still may have some future value though, editing posts
# took a decent bit of work to program

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

################################################################################

def _send(msg=''):
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
class _PostEditor:

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
