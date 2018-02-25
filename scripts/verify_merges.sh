#! /bin/bash

#    Copyright (C) 2014-2018 Bill Winslow
#    Copyright (C) 2017-2018 Christian Beer
#
#    This script is a part of the mfaliquot package.
#
#    This program is libre software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
#    See the LICENSE file for more details.

aliqueit="./aliqueit"
mergefile="./allseq.merges.txt"
errfile="./allseq.broken.txt"
emailscript="/usr/bin/env python3 ./send_email.py"

if [[ ! -s $mergefile ]]; then exit 1; fi

if [[ ! -f $aliqueit || ! -x $aliqueit ]]; then
	$emailscript "Could not find aliqueit executable at $aliqueit"
fi

for line in $(cat $mergefile); do
	error=0
	allelf=""
	# read $line into array $seqs using _ as delimiter
	readarray -td_ seqs <<<"${line}_"; unset 'seqs[-1]';
	for seq in "${seqs[@]}"; do
		if [[ ! -s "alq_$seq.elf" ]]; then
			wget "http://factordb.com/elf.php?seq=$seq&type=1" -O "alq_$seq.elf"
		fi
		allelf="${allelf} alq_$seq.elf"
		if $aliqueit -t $seq; then
			# cut away index number to determine common index value
			cut -d . -f 2 alq_$seq.elf > alq_$seq.txt
		else
			error=1
			break
		fi
  done
	if [[ $error -gt 0 ]]; then
		echo "$line" >> $errfile
	else
		# determine common index (first line that is present in all alq_*.txt files)
		ci=$(grep -F -h -f alq_${seqs[0]}.txt alq_*.txt | head -n1)
		# find common index in all sequences and prepare for output
		out=$(grep -F "$ci" $allelf)
		$emailscript "Sequences verified as merged: $out"
		# delete temporary files
		for seq in "${seqs[@]}"; do
			rm "alq_$seq.elf" "alq_$seq.txt"
		done
	fi
done

echo > $mergefile

if [[ -s $errfile ]]; then
	$emailscript "Something is wrong with those sequences: $(cat $errfile)"
fi
