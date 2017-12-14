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

import logging
_logger = logging.getLogger(__name__)

from urllib import request, parse, error
#from http.cookiejar import CookieJar
#def add_cookies():
#     request.install_opener(request.build_opener(request.HTTPCookieProcessor(CookieJar())))

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
          page = request.urlopen(req, data).read().decode(encoding)
     except error.HTTPError as e:
          _logger.exception(f'{type(e).__name__}: {str(e)}', exc_info=e)
          return None
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
     # TODO: ^ that's pretty darn ugly, surely there's a better way?
     dictConfig(logconf)
     LOGGER = logging.getLogger()
     LOGGER.info(strftime('%Y-%m-%d %H:%M:%S'))
     return CONFIG, LOGGER
