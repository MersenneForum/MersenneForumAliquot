#!/bin/bash

webdir="/var/www/rechenkraft.net/aliquot/"

cp $webdir/AllSeq.html ../website/generated/
cp $webdir/AllSeq.txt ../website/generated/
cp $webdir/AllSeq.json ../website/generated/
cp $webdir/statistics.html ../website/generated/
cp $webdir/statistics.json ../website/generated/

