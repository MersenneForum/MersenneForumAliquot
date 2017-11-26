#! /usr/bin/env python3
# This is written to Python 3.3 standards
# indentation: 5 spaces (personal preference)
# when making large scope switches (e.g. between def or class blocks) use two
# blank lines for clearer visual separation

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

from os.path import realpath, join, dirname, exists
import sys
sys.path.insert(0, realpath(join(dirname(sys.argv[0]), '..')))

from mfaliquot.application import reservations as R
from mfaliquot.application import SequencesManager
from os import remove as rm
from shutil import copy2 as cp
from os.path import exists, realpath, join, dirname
import unittest


class TestSequencesManager(unittest.TestCase):

     snapshot = 'json_snapshot'
     txtsnapshot = 'txt_snapshot'
     file = 'test_AllSeq.json'
     txtfile = 'test_AllSeq.txt'
     lockfile = file + SequencesManager.lock_suffix


     def setUp(self):
          cp(self.snapshot, self.file)
          try:
               rm(self.lockfile)
          except:
               pass
          try:
               rm(self.txtfile)
          except:
               pass


     def test_manual_lock_unlock(self):
          seqinfo = SequencesManager(self.file)

          seqinfo.lock_read_init()

          self.assertTrue(exists(self.lockfile))
          self.assertFalse(exists(self.txtfile))

          seqinfo.unlock_write()

          self.assertFalse(exists(self.lockfile))
          self.assertTrue(exists(self.txtfile))

          self.assertFilesEqual(seqinfo.file, self.snapshot)
          self.assertFilesEqual(self.txtfile, self.txtsnapshot)


     def test_auto_lock_unlock(self):
          seqinfo = SequencesManager(self.file)
          self.assertFalse(exists(self.txtfile))

          with seqinfo.acquire_lock(block_minutes=0):
               self.assertTrue(exists(self.lockfile))
               self.assertFalse(exists(self.txtfile))

          self.assertFalse(exists(self.lockfile))
          self.assertTrue(exists(self.txtfile))

          self.assertFilesEqual(seqinfo.file, self.snapshot)
          self.assertFilesEqual(self.txtfile, self.txtsnapshot)



     def assertFilesEqual(self, f1, f2):
          with open(f1) as f:
               s1 = f.read()
          with open(f2) as f:
               s2 = f.read()
          self.assertEqual(s1, s2)



#class ReservationsTest(unittest.TestCase):
#
#     def test_AliquotReservations(self):
#          res, count = AliquotReservations.read_file('res_file_snapshot_pre')
#
#          self.assertEqual(count, 23)
#          self.assertIsNotNone(res._when)
#          self.assertEqual(strftime(DATEFMT, res._when), '2017-11-14 13:50:21')
#          self.assertListEqual(list(sorted(res._db.keys())),
#               [276, 552, 564, 660, 966, 1074, 1134, 1464, 1476, 1512, 1560, 1578, 1632, 1734, 1992, 2232, 2340, 2360, 2484, 2514, 2664, 2712, 2982])
#
#          ######################################################################
#
#          already, other = res.reserve_seqs('mersenneforum', [3366, 276, 552, 1464])
#
#          self.assertListEqual(already, [276])
#          self.assertListEqual(other, [(552, 'Paul Zimmermann'), (1464, 'christophe.clavier')])
#          self.assertEqual(len(res._db), 24)
#
#          ######################################################################
#
#          notres, wrong, c = res.unreserve_seqs('Walter Krickau', [1578])
#
#          self.assertFalse(notres)
#          self.assertFalse(wrong)
#          self.assertEqual(c, 1)
#          self.assertEqual(len(res._db), 23)
#
#          ######################################################################
#
#          notres, wrong, c = res.unreserve_seqs('fivemack', [4788, 2232, 2340, 2360, 966, 276])
#
#          self.assertEqual(c, 3)
#          self.assertEqual(len(res._db), 20)
#          self.assertListEqual(notres, [4788])
#          self.assertListEqual(wrong, [(966, 'Paul Zimmermann'), (276, 'mersenneforum')])
#
#          ######################################################################
#
#          adds, drops = res.apply_to_seqinfo(_SEQINFO) #TODO: bug if SEQINFO is itself in error(/out of date)! rewrite from scratch.
#
#          self.assertEqual(len(res._db), 20)
#          self.assertTupleEqual((adds, drops), (1, 4))
#
#          ######################################################################
#
#          c = res.write_to_file('res_file_snapshot_post', seqinfo=_SEQINFO)
#
#          self.assertEqual(c, 20)
#          with open('res_file_snapshot_post', 'r') as f:
#               self.assertEqual(f.read(), _POSTTESTSTR)




#_SEQINFO = {x[0]: AliquotSequence(lst=x) for x in \


if __name__ == '__main__':
     unittest.main()
