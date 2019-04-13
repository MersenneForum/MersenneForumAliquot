#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
scl enable rh-python36 "./filter_seqs.py \"(ali.res=='yafu@home')\" \"(ali.priority)\" 20 \" \"" > ../tmp/update_yafu.txt

scl enable rh-python36 "./allseq.py `cat ../tmp/update_yafu.txt`" > /dev/null 2>&1

