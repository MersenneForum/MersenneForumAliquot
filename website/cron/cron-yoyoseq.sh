#!/bin/bash

grep yafu /var/www/rechenkraft.net/aliquot/reservations| sort -k 4 -n | head -50 | cut -b1-7 | xargs > /tmp/yafus.txt

scl enable python33 "/home/christianb/bin/allseq.py `cat /tmp/yafus.txt`" >> /home/christianb/bin/log/yoyoseq.log 2>&1

scl enable python33 "/home/christianb/bin/allseq.py 4788" >> /home/christianb/bin/log/yoyoseq.log 2>&1

