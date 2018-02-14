#! /bin/bash

#    Copyright (C) 2014-2018 Bill Winslow
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

aliqueit="/home/bill/aliqueit/aliqueit"
termfile="./allseq.terms.txt"
errfile="./allseq.broken.txt"
goodfile="./allseq.checked.txt"
emailscript="/usr/bin/env python3 ./send_email.py"


if [[ ! -s $termfile ]]; then exit 1; fi

for seq in $(cat $termfile); do
	if [[ ! -s "alq_$seq.elf" ]]; then
		wget "http://factordb.com/elf.php?seq=$seq&type=1" -O "alq_$seq.elf"
	fi
	if $aliqueit -t $seq; then
		rm "alq_$seq.elf"
		echo "$seq" >> $goodfile # positive verification that script executed
	else
		echo "$seq" >> $errfile
	fi
done

echo > $termfile

if [[ -s $errfile ]]; then
	$emailscript "Sequences failed to verify as terminated: $(cat $errfile)"
fi
