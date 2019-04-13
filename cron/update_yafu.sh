#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts
./filter_seqs.py "(ali.res=='yafu@home')" "(ali.priority)" 20 " " > ../tmp/update_yafu.txt

./allseq.py `cat ../tmp/update_yafu.txt` > /dev/null 2>&1

