#! /usr/bin/python3

import smtplib
from email.utils import formatdate
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(to, frm, sbjct, txt, host, port, tls=True, acct=None, pswd=None):
     """To, From, Subject, Body, Server, Port, Account, Password"""
     msg = MIMEMultipart()

     if isinstance(to, list):
          to = ', '.join(to)
     msg['To'] = to
     msg['Subject'] = sbjct
     msg['From'] = frm
     msg['Date'] = formatdate(localtime=True)

     msg.attach(MIMEText(txt))

     server = smtplib.SMTP(host, port)
     if tls:
          server.starttls()
     if acct or pswd:
          server.login(acct, pswd)
     server.send_message(msg)
