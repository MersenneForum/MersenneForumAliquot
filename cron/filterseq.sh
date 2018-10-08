#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
scl enable rh-python36 "./filter_seqs.py \"isinstance(ali.cofactor, int) and ali.priority < 6\" \"(ali.size, ali.cofactor)\" 100 \" \"" >> ../tmp/filterseq.txt

scl enable rh-python36 "./allseq.py `cat ../tmp/filterseq.txt`" > /dev/null 2>&1

