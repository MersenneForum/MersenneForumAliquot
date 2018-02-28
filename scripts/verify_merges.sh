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
emailscript="./send_email.py"

if [[ ! -s $mergefile ]]; then exit 1; fi

if [[ ! -f $aliqueit || ! -x $aliqueit ]]; then
	$emailscript "Could not find aliqueit executable at $aliqueit"
fi

out="Sequences verified as merged:\n"

while read line; do
	error=0
	seqs=(${line})
	for seq in "${seqs[@]}"; do
		if [[ ! -s "alq_$seq.elf" ]]; then
			wget "http://factordb.com/elf.php?seq=$seq&type=1" -O "alq_$seq.elf"
		fi
		if $aliqueit -t $seq; then
			# cut away index number to determine common index value
			cut -d . -f 2 alq_$seq.elf > alq_$seq.txt
		else
			error=1
			echo "$seq failed to verificate" >> $errfile
			break
		fi
	done
	if [[ $error -gt 0 ]]; then
		echo "$line" >> $errfile
	else
		first="${seqs[0]}"
		other="${seqs[@]:1}"
		for seq in $other; do
			# determine common index (first line that is present in all alq_*.txt files)
			ci=$(grep -F -h -f "alq_$first.txt" "alq_$seq.txt" | head -n 1)

			# find common index between the two sequences and prepare for output
			merger=$(grep -B 1 -F "$ci" "alq_$first.elf" "alq_$seq.elf")
			out="$out\n$merger\n\n"

			# delete temporary files
			rm "alq_$seq.elf" "alq_$seq.txt"
		done
		rm "alq_$first.elf" "alq_$first.txt"
	fi
done < $mergefile

$emailscript "$(echo -e "$out")" # echo -e to interpret the \n to actual newlines

echo > $mergefile

if [[ -s $errfile ]]; then
	$emailscript "Something is wrong with these sequences: $(cat $errfile)"
fi
