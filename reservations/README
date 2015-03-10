Run this from cron to automagically update the MersenneForum Aliquot reservation thread's head post.
You need to change the working directory and login credentials in the script.
Like the website scripts, I would redirect stdout and stderr to a log file and check up on it from
time to time.

Currently, any line with any of these keywords:
'Reserv', 'reserv', 'Add', 'add', 'Tak', 'tak'
with 5 or 6 digit numbers, is assumed to be a reservation made by the poster; any line with these keywords:
'Unreserv', 'unreserv', 'Drop', 'drop', 'Releas', 'releas'
and 5 or 6 digit numbers is treated as a drop.

Reservations by non-members can still be edited in to the head post as before; the script always
gets the current reservations from there, so those changes are preserved. However, text outside
the reservation list is *not* preserved; instead modify the template at the top of the script.

Note that before initial use you just put the most recent post ID in the file described by the script.

Report any problems on Github or via MF PM.
