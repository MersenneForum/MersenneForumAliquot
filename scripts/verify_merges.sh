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
	alltxt=""
	# read $line into array $seqs using _ as delimiter
	readarray -td_ seqs <<<"${line}_"; unset 'seqs[-1]';
	for seq in "${seqs[@]}"; do
		if [[ ! -s "alq_$seq.elf" ]]; then
			wget "http://factordb.com/elf.php?seq=$seq&type=1" -O "alq_$seq.elf"
		fi
		allelf="${allelf} alq_$seq.elf"
		alltxt="${alltxt} alq_$seq.txt"
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
		# to find common lines between unsorted files, use grep -f -- the key is
		# that the file proving the patterns must be excluded from files to be
		# searched. Split alltxt between first and rest.
		firsttxt=$(echo "$alltxt" | cut -d ' ' -f 1)
		othertxt=$(echo "$alltxt" | cut -d ' ' -f 1 --complement)
		# I'm pretty sure this is all totally silly, and it would be cleaner to
		# construct onetxt/alltxt/allelf by using the $seqs array, but damned if I
		# know how arrays work in bash, and this certainly works even if it's horribly
		# inelegant

		# determine common index (first line that is present in all alq_*.txt files)
		ci=$(grep -F -h -f $firsttxt $othertxt | head -n 1)
		# find common index in all sequences and prepare for output
		out=$(grep -B 1 -F "$ci" $allelf)
		$emailscript "$(echo -e "Sequences verified as merged:\n$out")"
		# delete temporary files
		for seq in "${seqs[@]}"; do
			rm "alq_$seq.elf" "alq_$seq.txt"
		done
	fi
done

echo > $mergefile

if [[ -s $errfile ]]; then
	$emailscript "Something is wrong with these sequences: $(cat $errfile)"
fi
