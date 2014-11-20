#!/usr/bin/env python

from mechanize import Browser
from lxml import html, etree

import json
import os
import random
import re
import sys
import time
import urllib
import urlparse


USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:33.0) Gecko/20100101 Firefox/33.0'
OSTYPE = 'MacOS10.10.1'


def to_dict(dict_str):
    class _dict(dict):
        def __getitem__(self, key):
            return key
    return eval(dict_str, _dict())


def ror(a, b):
    c = 0
    while c < b:
        a = (0x7fffffff & (a >> 1)) + (0x80000000 & (a << 31))
        c += 1
    return a


def get_tkey(tm=None):
    l2 = 773625421
    if not tm:
        tm = int(time.time())
    l3 = ror(tm, l2 % 13)
    l3 ^= l2
    l3 = ror(l3, l2 % 17)
    if l3 & 0x80000000:
        return l3 - 0x100000000
    return l3


def download_m3u8(browser, playlist, target_file, duration):
    of = open(target_file, 'wb')
    resp = browser.open(playlist)
    ddu = 0
    dsz = 0
    start_time = time.time()
    for line in resp.readlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            if line.startswith('#EXTINF:'):
                ddu += float(line[8:-1])
            continue
        ts = time.time()
        resp = browser.open(line)
        data = resp.read()
        of.write(data)
        dsz += len(data)
        ts = time.time() - ts
        speed = (len(data)/1024)/ts
        print "[%%%d] %dKB/s %d/%s\r" % (ddu*100/duration, speed, dsz, '??'),
        sys.stdout.flush()
    
    total_time = time.time() - start_time

    of.close()

    print 'Total Size: %d' % dsz
    print 'Download in %ds, speed %dKB/s' % (total_time, dsz/total_time)

def get_playjson(vid, nextvid, target_dir):
    browser = Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [
        ('User-Agent', USER_AGENT),
        ('Referer', 'http://player.letvcdn.com/p/201411/14/10/newplayer/LetvPlayer.swf')
    ]

    param_dict = {
        'id': vid,
        'platid': 1,
        'splatid': 101,
        'format': 1,
        'nextvid': nextvid,
        'tkey': get_tkey(),
        'domain': 'www.letv.com'
    }

    url = 'http://api.letv.com/mms/out/video/playJson?%s' % urllib.urlencode(param_dict)
    resp = browser.open(url)
    resp_body = resp.read()
    resp_dict = json.loads(resp_body)

    assert resp_dict['statuscode'] == '1001'
    assert resp_dict['playstatus']['status'] == '1'

    playurls = resp_dict['playurl']['dispatch']
    domains = resp_dict['playurl']['domain']
    duration = int(resp_dict['playurl']['duration'])

    print 'Avaliable Size:', ' '.join(playurls.keys())
    keys = ['1080p', '720p', '1300', '1000', '350']
    for key in keys:
        playurl = playurls.get(key)
        if playurl:
            break

    print 'Select %s' % key
    assert playurl

    tn = random.random()
    url = domains[0] + playurl[0] + '&ctv=pc&m3v=1&termid=1&format=1&hwtype=un&ostype=%s&tag=letv&sign=letv&expect=3&tn=%s&pay=0&rateid=%s' % (OSTYPE, tn, key)
    resp = browser.open(url)
    gslb_data = json.loads(resp.read())

#    import pprint
#    pprint.pprint(resp_dict)
#    pprint.pprint(gslb_data)
    play_url = gslb_data.get('location')

    file_name_m3u8 = os.path.basename(urlparse.urlsplit(play_url).path)
    file_name = '%s.ts' % os.path.splitext(file_name_m3u8)[0]
    target_file = os.path.join(target_dir, file_name)

    print 'Save to %s' % target_file
    download_m3u8(browser, play_url, target_file, duration)

    return resp_dict


def letv(page_url, target_dir):
    browser = Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [('User-Agent', USER_AGENT)]

    resp = browser.open(page_url)
    resp_body = resp.read()
    tree = html.fromstring(resp_body)
    for script in tree.xpath('/html/head/script'):
        match_info = []
        start = False
        if not script.text:
            continue
        for line in script.text.split('\n'):
            if not start:
                match = re.match('var\s+__INFO__\s?=(.+)', line)
                if match:
                    start = True
                    match_info.append(match.group(1))
            else:
                if line.startswith('var'):
                    start = False
                    break
                hp = line.find('://')
                p = line.rfind('//')
                if p != -1 and p != hp+1:
                    match_info.append(line[:p])
                else:
                    match_info.append(line)
        if match_info:
            break
    match_info = '\n'.join(match_info)
    match_info = to_dict(match_info)
    vid = match_info['video']['vid']
    nextvid = match_info['video']['nextvid']
    print '%s' % match_info['video']['title']
    play_json = get_playjson(vid, nextvid, target_dir)


if __name__ == '__main__':
    page_url = sys.argv[1]
    target_dir = sys.argv[2]
    letv(page_url, target_dir)
