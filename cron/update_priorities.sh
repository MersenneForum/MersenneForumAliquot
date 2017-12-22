#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts/
scl enable rh-python36 "./update_priorities.py" >> $HOME/MersenneForumAliquot/log/cron-update_priorities.log 2>&1
