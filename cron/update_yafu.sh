#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
scl enable rh-python36 "./filter_seqs.py \"(ali.res=='yafu@home' and ali.priority > 100)\" \"(-ali.priority)\" 50 \" \"" > ../tmp/update_yafu.txt

scl enable rh-python36 "./allseq.py `cat ../tmp/update_yafu.txt`" > /dev/null 2>&1

