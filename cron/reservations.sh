#!/bin/bash
cd $HOME/MersenneForumAliquot/scripts/
scl enable rh-python36 "./reservations.py spider" > /dev/null 2>&1
