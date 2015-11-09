#! /usr/bin/env python3

import re

composite = re.compile(r' <a href="index.php\?id=([0-9]+?)"><font color="#002099">[0-9.]+?</font></a><sub>&lt;')
smallfact = re.compile(r' <a href="index.php\?id=[0-9]+?"><font color="#000000">([0-9^]+?)</font></a>')
largefact = re.compile(r' <a href="index.php\id=([0-9]+?)"><font color="#000000">[0-9]+?[.]{3}[0-9]{2}</font></a><sub>&lt;')
composite = re.compile(r'= <a.+<font color="#002099">[0-9.]+</font></a><sub>&lt;(?P<C>[0-9]+)')
smallfact = re.compile(r'(?:<font color="#000000">)([0-9^]+)(?:</font></a>)(?!<sub>)')
largefact = re.compile(r'(?:<font color="#000000">[0-9^.]+</font></a><sub>&lt;)([0-9]+)')
stuff = re.compile('<td bgcolor="#BBBBBB">n</td>\n<td bgcolor="#BBBBBB">Digits</td>\n<td bgcolor="#BBBBBB">Number</td>\n</tr><tr><td bgcolor="#DDDDDD">.{1,3}hecked</td>\n<td bgcolor="#DDDDDD">(?P<index>[0-9]+)</td>\n<td bgcolor="#DDDDDD">(?P<size>[0-9]+) <a href="index.php\\?showid=(?P<id>[0-9]+)">\\(show\\)')
created = re.compile('([JFMASOND][a-z]{2,8}) ([0-9]{1,2}), ([0-9]{4})') # strftime('%d', strptime(month, "%B"))
#oldpage = re.compile('(<tr> <td>([0-9]+?)</td> <td>([0-9]+?)</td>.*?<td>)[0-9A-Za-z_ ]*?</td> </tr>') # Kept for historical purposes
#oldjson = re.compile(r'(\[([0-9]+?), ([0-9]+?), ([0-9]+?), .*?)[0-9A-Za-z_ ]*?"\]') # Ditto
largenum = re.compile(r'<td align="center">(([0-9\s]|(<br>))+?)</td>')
