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
          Print('HTTPError:', e)
          return None
     except Exception as e:
          Print('{}!'.format(type(e)), e)
          return None
     else:
          return page

