#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts/
scl enable rh-python36 "./reservations.py" >> $HOME/MersenneForumAliquot/log/cron-reservations.log 2>&1
