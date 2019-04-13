#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
./filter_seqs.py "isinstance(ali.cofactor, int) and ali.priority < 6" "(ali.size, ali.cofactor)" 100 " " >> ../tmp/filterseq.txt

./allseq.py `cat ../tmp/filterseq.txt` > /dev/null 2>&1

