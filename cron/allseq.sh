#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
scl enable rh-python36 "./allseq.py" >> $HOME/MersenneForumAliquot/log/allseq.log 2>&1

