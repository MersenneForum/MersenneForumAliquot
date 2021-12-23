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

import logging
_logger = logging.getLogger(__name__)

from urllib import request, parse, error
from socket import timeout
#from http.cookiejar import CookieJar
#def add_cookies():
#     request.install_opener(request.build_opener(request.HTTPCookieProcessor(CookieJar())))

#from http.client import HTTPConnection
#HTTPConnection.debuglevel = 1

def blogotubes(url, encoding='utf-8', hdrs=None, data=None):
     if hdrs is None:
          hdrs = {}
     if data is not None:
          data = parse.urlencode(data, encoding=encoding)
          data = data.encode(encoding)
          #hdrs['Content-Type'] = 'application/x-www-form-urlencoded;charset='+encoding
     #req = request.Request(parse.quote(url, safe='/:'), headers=hdrs)
     req = request.Request(url, headers=hdrs)
     try:
          page = request.urlopen(req, data, timeout=300).read().decode(encoding) # 5 min timeout
     except error.HTTPError as e:
          _logger.exception(f'{type(e).__name__}: {str(e)}', exc_info=e)
          return None
     except error.URLError as e:
          _logger.exception(f'{type(e).__name__}: {str(e)}', exc_info=e)
          return None
     except timeout:
          _logger.exception(f'socket timed out - URL %s', url)
     except Exception as e:
          _logger.exception(f'{type(e).__name__}: {str(e)}', exc_info=e)
          return None
     else:
          return page


from collections import OrderedDict
from collections.abc import MutableMapping
import json

class InterpolatedJSONConfig(OrderedDict):
     '''A class to allow human-readable text configuration, without the complicated and
     historical API of the stdlib's ConfigParser. Example:

     >>> ijc = InterpolatedJSONConfig()
     >>> test = {"akey": 2, "bkey": "notmplstr", "ckey": "a formatted str: {akey}", "dkey": {"ekey": "nested val", "fkey": "nested formatted val: {akey}  (with nested formattings:) {dkey[ekey]}!!"}}
     >>> ijc.update(test)
     >>> ijc
     InterpolatedJSONConfig([('akey', 2), ('bkey', 'notmplstr'), ('ckey', 'a formatted str: 2'), ('dkey', {'ekey': 'nested val', 'fkey': 'nested formatted val: 2  (with nested formattings:) nested val!!'})])

     Caution: dynamically adding further dicts requires manually calling interpolate() on those
     dicts as well.
     '''

     def update(self, other):
          super().update(other)
          self.interpolate(other, _smooshed=True)


     def read_file(self, file):
          with open(file) as f:
               d = json.load(f, object_pairs_hook=OrderedDict)
          self.update(d)


     def interpolate(self, dct, *, _smooshed=False):
          # _smooshed is true for toplevel dcts which have already been `update`d to self
          stodo, dtodo = [], []
          for key, val in dct.items():
               if isinstance(val, str) and ('{' in val or '}' in val):
                    stodo.append((key,val))
               elif isinstance(val, MutableMapping):
                    dtodo.append(val)

          for key, s in stodo:
               tmp = s.format_map(self) # allow absolute only references (for now?)
               if _smooshed:
                    self[key] = tmp
               else:
                    dct[key] = tmp
          for d in dtodo:
               self.interpolate(d)


from time import strftime

def config_boilerplate(CONFIGFILE, SCRIPTNAME):
     from logging.config import dictConfig
     CONFIG = InterpolatedJSONConfig()
     CONFIG.read_file(CONFIGFILE)
     logconf = CONFIG['logging']

     file_handler = logconf['handlers']['file_handler']
     file_handler['filename'] = file_handler['filename'].format(SCRIPTNAME)
     email_handler = logconf['handlers']['email_handler']
     email_handler['scriptname'] = email_handler['scriptname'].format(SCRIPTNAME)
     # TODO: ^ that's pretty darn ugly, surely there's a better way?

     dictConfig(logconf)
     LOGGER = logging.getLogger()
     LOGGER.info(strftime('%Y-%m-%d %H:%M:%S'))
     return CONFIG, LOGGER


from smtplib import SMTP, SMTPException
from email.message import EmailMessage

class BufferingSMTPHandler(logging.Handler):

     # Don't try to send emails about logging records reporting email errors
     _special_attr = 'SMTPException'
     _special_kwarg = {_special_attr: True}

     @classmethod
     def _smtpfilter(klass, record):
          if hasattr(record, klass._special_attr):
               return False
          return True


     def __init__(self, host, from_addr, to_addrs, scriptname, port=None, username=None, password=None):
          super().__init__()
          self.buffer = []
          self.host = host
          self.port = port
          self.from_addr = from_addr
          self.to_addrs = to_addrs
          self.scriptname = scriptname
          self.username = username
          self.password = password
          self.addFilter(self._smtpfilter)


     def emit(self, record):
          self.buffer.append(record)


     def flush(self):
          # Add extra newline to info() messages for separation in logfile
          if not self.buffer:
               _logger.info("No warnings, no email to send\n")
               return
          _logger.info(f"Sending logging email with {len(self.buffer)} records\n")
          txt = ''.join(self.format(record)+'\n' for record in self.buffer)
          msg = EmailMessage()
          msg['Subject'] = "mfaliquot: {}.py has something to say".format(self.scriptname)
          msg['To'] = ', '.join(self.to_addrs)
          msg['From'] = self.from_addr
          msg.set_content("Something went wrong (?) while {}.py was running:\n\n".format(self.scriptname)+txt)
          try:
               s = SMTP(self.host)
               s.connect(self.host, self.port)
               s.starttls()
               if self.username and self.password:
                    s.login(self.username, self.password)
               s.send_message(msg)
               s.quit()
          except SMTPException as e:
               _logger.exception("Logging email failed to send:", exc_info=e, extra=self._special_kwarg)
          except OSError as e:
               _logger.exception("Some sort of smtp problem:", exc_info=e, extra=self._special_kwarg)
          except BaseException as e:
               _logger.exception("Unknown error while attempting to email:", exc_info=e, extra=self._special_kwarg)
          else:
               self.buffer.clear()

