#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
scl enable rh-python36 "./filter_seqs.py \"isinstance(ali.cofact, int)\" \"(ali.cofact, ali.time)\" 50 \" \"" >> ../tmp/filterseq.txt

scl enable rh-python36 "./allseq.py `cat ../tmp/filterseq.txt`" > /dev/null 2>&1

