#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
scl enable rh-python36 "./filter_seqs.py" >> ../tmp/filterseq.txt

scl enable rh-python36 "./allseq.py `cat ../tmp/filterseq.txt`" >> ../log/filterseq.log 2>&1

