#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts

if [ ! -e pointer ]; then
  echo 0 > pointer
fi

input="../tmp/u2d_2e6.txt"
last_pos=$(head -n 1 pointer)
num_seqs=50

newseqs=""

cur_pos=0
while [[ $num_seqs -gt 0 ]]; do
  read -r alq
  if [[ $cur_pos -lt $last_pos ]]; then
    cur_pos=$((cur_pos+1))
    continue
  fi
  newseqs="${newseqs} ${alq}"
  num_seqs=$((num_seqs-1))
  cur_pos=$((cur_pos+1))
done < "$input"

./allseq.py $newseqs > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo $cur_pos > pointer
fi

