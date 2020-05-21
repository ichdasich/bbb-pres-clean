#!/usr/bin/python3

import sys
import subprocess
import re
import hashlib
import requests
import glob
import shutil
import os
import time
from xml.etree import ElementTree

###
## bbb-conf --secret
#
#    URL: https://.../bigbluebutton/
#    Secret: ....
#

verbose = False
if len(sys.argv) > 1 and sys.argv[1] == '-v':
	verbose = True

tmp = subprocess.run(['/usr/bin/bbb-conf', '--secret'], stdout=subprocess.PIPE, universal_newlines=True)
#PYTHON 3.7 tmp = subprocess.run(['/usr/bin/bbb-conf', '--secret'], capture_output=True, text=True)
output = tmp.stdout

URL = None
secret = None

for line in output.splitlines():
	m = re.search('URL: (?P<URL>.*/bigbluebutton/)', line)
	if m:
		URL = m.group('URL')
		continue
	m = re.search('Secret: (?P<secret>.*)$', line)
	if m:
		secret = m.group('secret')


if not URL or not secret:
	print('error getting URL and/or secret. Is "bbb-conf --secret" returning it?')

APIURL=URL + 'api/'

apimethod='getMeetings'
querystring=''

h = hashlib.sha1((apimethod+querystring+secret).encode('utf-8'))
checksum = h.hexdigest()

if len(querystring) > 0:
	querystring = querystring + '&'

requesturl = APIURL + apimethod + '?' + querystring + 'checksum=' + checksum

response = requests.get(requesturl)
tree = ElementTree.fromstring(response.content)

if tree.find('returncode').text != 'SUCCESS':
	print('error getting API data')
	sys.exit(1)
meetings = tree.find('meetings')

pres_files = glob.glob('/var/bigbluebutton/*-*')
caption_files = glob.glob('/var/bigbluebutton/captions/*')
status_files = glob.glob('/var/bigbluebutton/recording/status/archived/*fail')
pres_files = pres_files + caption_files

recorded_files = glob.glob('/var/bigbluebutton/recording/status/recorded/*.done')
processing_files = glob.glob('/var/bigbluebutton/recording/raw/*-*')
to_del = []

time.sleep(15)

for pres in pres_files:
	running = False
	recorded = False
	processing = False
	for m in meetings.iter('meeting'):
		meetid_int = m.find('internalMeetingID').text
		if meetid_int in pres:
			running = True
	for r in recorded_files:
		meetid_int = r.split('/')[-1].split('.')[0]
		if meetid_int in pres:
			recorded = True
	for p in processing_files:
		meetid_int = p.split('/')[-1]
		if meetid_int in pres:
			processing = True
	if not running and not recorded and not processing:
		to_del.append(pres)


for d in to_del:
	try:
		shutil.rmtree(d)
	except:
		pass

for d in status_files:
	try:
		os.remove(d)
	except:
		pass
