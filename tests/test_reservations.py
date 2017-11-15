#! /usr/bin/env python3
# indentation: 5 spaces (personal preference)

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
from os.path import realpath, join, dirname
sys.path.insert(0, realpath(join(dirname(sys.argv[0]), '..')))

from mfaliquot.reservations import AliquotReservations, DATEFMT
from mfaliquot.sequence import AliquotSequence
from time import strftime
import unittest as ut

class ReservationsTest(ut.TestCase):

     def test_AliquotReservations(self):
          res, count = AliquotReservations.read_file('res_file_snapshot_pre')

          self.assertEqual(count, 23)
          self.assertIsNotNone(res._when)
          self.assertEqual(strftime(DATEFMT, res._when), '2017-11-14 13:50:21')
          self.assertListEqual(list(sorted(res._db.keys())),
               [276, 552, 564, 660, 966, 1074, 1134, 1464, 1476, 1512, 1560, 1578, 1632, 1734, 1992, 2232, 2340, 2360, 2484, 2514, 2664, 2712, 2982])

          ######################################################################

          already, other = res.reserve_seqs('mersenneforum', [3366, 276, 552, 1464])

          self.assertListEqual(already, [276])
          self.assertListEqual(other, [(552, 'Paul Zimmermann'), (1464, 'christophe.clavier')])
          self.assertEqual(len(res._db), 24)

          ######################################################################

          notres, wrong, c = res.unreserve_seqs('Walter Krickau', [1578])

          self.assertFalse(notres)
          self.assertFalse(wrong)
          self.assertEqual(c, 1)
          self.assertEqual(len(res._db), 23)

          ######################################################################

          notres, wrong, c = res.unreserve_seqs('fivemack', [4788, 2232, 2340, 2360, 966, 276])

          self.assertEqual(c, 3)
          self.assertEqual(len(res._db), 20)
          self.assertListEqual(notres, [4788])
          self.assertListEqual(wrong, [(966, 'Paul Zimmermann'), (276, 'mersenneforum')])

          ######################################################################

          adds, drops = res.apply_to_seqinfo(_SEQINFO) #TODO: bug if SEQINFO is itself in error(/out of date)! rewrite from scratch.

          self.assertEqual(len(res._db), 20)
          self.assertTupleEqual((adds, drops), (1, 4))

          ######################################################################

          c = res.write_to_file('res_file_snapshot_post', seqinfo=_SEQINFO)

          self.assertEqual(c, 20)
          with open('res_file_snapshot_post', 'r') as f:
               self.assertEqual(f.read(), _POSTTESTSTR)




_SEQINFO = {x[0]: AliquotSequence(lst=x) for x in \
[[276, 211, 2122, 1100000000968464132, "2 * 3", "2 * 3^2 * 7 * 19 * 709 * C205", 205, 1, "2017-11-14 01:17:02", "2017-09-12", "mersenneforum", True],
 [552, 193, 1135, 1100000000928411922, "2^2", "2^2 * 3 * 11 * 197 * 4937461 * C182", 182, 2, "2017-11-14 01:17:03", "2017-05-07", "Paul Zimmermann", False],
 [564, 199, 3466, 1100000000973607749, "2^4", "2^4 * 71 * 2237 * P29 * C164", 164, 4, "2017-11-14 01:17:04", "2017-09-17", "Paul Zimmermann", False],
 [660, 197, 978, 1100000001065355300, "2^2", "2^2 * P36 * C162", 162, 2, "2017-11-14 06:03:22", "2017-11-13", "Paul Zimmermann", False],
 [966, 197, 994, 1100000000967742487, "2^4", "2^4 * 5 * 7 * 399566813 * C186", 186, 4, "2017-11-14 01:17:07", "2017-09-10", "Paul Zimmermann", False],
 [1074, 197, 2172, 1100000000933882636, "2^3 * 3", "2^3 * 3 * 11 * 29 * 3000539 * 17242399 * C179", 179, 1, "2017-11-14 01:17:08", "2017-05-21", "Paul Zimmermann", True],
 [1134, 192, 3824, 1100000001054089684, "2^2 * 7", "2^2 * 5 * 7 * 53 * 91270441 * C180", 180, -1, "2017-11-14 01:17:09", "2017-10-15", "Paul Zimmermann", True],
 [1464, 185, 2426, 1100000000954669192, "2^3 * 3", "2^3 * 3 * 12569 * P14 * C166", 166, 1, "2017-11-14 01:17:10", "2017-08-10", "christophe.clavi", True],
 [1476, 194, 1306, 1100000000954668277, "2^4", "2^4 * 3^2 * 5 * 13 * 1951879 * C183", 183, 4, "2017-11-14 01:17:16", "2017-08-10", "christophe.clavi", False],
 [1488, 180, 1612, 1100000000960867948, "2^3 * 3 * 5", "2^3 * 3 * 5 * 7 * 73 * 9839 * P13 * C158", 158, 0, "2017-11-14 01:17:18", "2017-08-22", "", True],
 [1512, 185, 2397, 1100000000954668519, "2^2", "2^2 * C184", 184, 2, "2017-11-14 01:17:19", "2017-08-10", "christophe.clavi", False],
 [1560, 201, 2016, 1100000000905607387, "2^3 * 3 * 5", "2^3 * 3 * 5 * 17 * 617 * C195", 195, 0, "2017-11-14 01:17:20", "2017-02-22", "christophe.clavi", True],
 [1578, 166, 7613, 1100000000954682771, "2 * 3", "2 * 3 * 5 * 17 * 23 * P22 * C140", 140, -1, "2017-11-14 01:17:21", "2017-08-11", "Walter Krickau", True],
 [1632, 165, 1527, 1100000000925281236, "2^3 * 3 * 5", "2^3 * 3 * 5 * 13 * 197 * C160", 160, 0, "2017-11-14 01:17:23", "2017-04-30", "christophe.clavi", True],
 [1734, 186, 2660, 1100000000905607661, "2^4", "2^4 * 7 * 13 * C183", 183, 4, "2017-11-14 01:17:24", "2017-02-22", "christophe.clavi", False],
 [1920, 191, 2615, 1100000000945545759, "2^2 * 7", "2^2 * 3^3 * 5 * 7^2 * 23 * P11 * C175", 175, 2, "2017-11-14 01:17:25", "2017-07-23", "", True],
 [1992, 173, 1599, 1100000001061977744, "2^2 * 7", "2^2 * 5 * 7 * 2308357 * C165", 165, -1, "2017-11-14 01:17:26", "2017-11-04", "christophe.clavi", True],
 [2232, 179, 1298, 1100000000938510300, "2 * 3", "2 * 3 * 269 * C175", 175, -1, "2017-11-14 01:17:27", "2017-07-02", "fivemack", True],
 [2340, 216, 790, 1100000000954681331, "2^5 * 3", "2^5 * 3^3 * 5 * 13 * 50951 * 1730441 * C201", 201, 2, "2017-11-14 01:17:28", "2017-08-10", "fivemack", False],
 [2360, 170, 1699, 1100000001054211748, "2^2", "2^2 * 11 * 13 * 317 * 3221 * C162", 162, 2, "2017-11-14 01:17:29", "2017-10-15", "fivemack", False],
 [2484, 188, 1623, 1100000000925281778, "2^3 * 3", "2^3 * 3 * C186", 186, 1, "2017-11-14 01:17:30", "2017-04-30", "christophe.clavi", True],
 [2514, 199, 3156, 1100000000827811698, "2^3 * 3", "2^3 * 3 * 11 * 13 * 6311 * C192", 192, 1, "2017-11-14 01:17:32", "2016-03-14", "christophe.clavi", True],
 [2664, 181, 1278, 1100000000905608215, "2^2 * 7", "2^2 * 7 * 63809 * C175", 175, -1, "2017-11-14 01:17:33", "2017-02-22", "christophe.clavi", True],
 [2712, 169, 1951, 1100000000826510606, "2^5 * 3 * 7", "2^5 * 3 * 7^2 * 11 * C164", 164, 3, "2017-11-14 01:17:34", "2016-03-07", "christophe.clavi", True],
 [2982, 182, 1465, 1100000000938510318, "2^3 * 3", "2^3 * 3^2 * 11 * 13 * 61 * 331 * 2213 * C170", 170, 3, "2017-11-14 01:17:35", "2017-07-02", "fivemack", True],
 [3270, 202, 722, 1100000000885857276, "2^7 * 3", "2^7 * 3 * 7 * 163 * C196", 196, 5, "2017-11-14 01:17:36", "2016-12-06", "", False],
 [3366, 199, 2180, 1100000000914717545, "2^3 * 3", "2^3 * 3 * 223 * C195", 195, 1, "2017-11-14 01:17:37", "2017-03-13", "mersenneforum", True]] }


_POSTTESTSTR = \
'''2017-11-14 13:50:21
   276  mersenneforum    2122  211
   552  Paul Zimmermann  1135  193
   564  Paul Zimmermann  3466  199
   660  Paul Zimmermann   978  197
   966  Paul Zimmermann   994  197
  1074  Paul Zimmermann  2172  197
  1134  Paul Zimmermann  3824  192
  1464  christophe.clavier  2426  185
  1476  christophe.clavier  1306  194
  1512  christophe.clavier  2397  185
  1560  christophe.clavier  2016  201
  1632  christophe.clavier  1527  165
  1734  christophe.clavier  2660  186
  1992  christophe.clavier  1599  173
  2484  christophe.clavier  1623  188
  2514  christophe.clavier  3156  199
  2664  christophe.clavier  1278  181
  2712  christophe.clavier  1951  169
  2982  fivemack         1465  182
  3366  mersenneforum    2180  199'''


if __name__ == '__main__':
     ut.main()
