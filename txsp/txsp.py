#!/usr/bin/env python

from mechanize import Browser
from lxml import etree, html

import os
import random
import re
import sys
import time
import urllib
import urllib2
import uuid

from echo_ckeyv3 import echo_ckeyv3

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:41.0) Gecko/20100101 Firefox/41.0'
SWF_REFERER = 'http://imgcache.qq.com/tencentvideo_v1/player/TencentPlayer.swf?max_age=86400&v=20151010'
PLATFORM = 11
PLAYER_GUID = uuid.uuid4().hex
PLAYER_PID = uuid.uuid4().hex
PLAYER_VERSION = '3.2.19.340'
KLIB_VERSION = '2.0'

def get_url(browser, page_url, working_dir=None):
    page_data = None
    if working_dir:
        filehash = md5(page_url)
        page_file = os.path.join(working_dir, filehash)
        if os.path.exists(page_file):
            page_data = open(page_file, 'rb').read()
    if not page_data:
        resp = browser.open(page_url)
        page_data = resp.read()
        if working_dir:
            open(page_file, 'wb').write(page_data)
    return html.fromstring(page_data)

def to_dict(json_object):
    class global_dict(dict):
        def __getitem__(self, key):
            return key
    return eval(json_object, global_dict())

def getvinfo(target_dir, url, vid):
    rand = random.random()
    ckey = echo_ckeyv3(vid, PLAYER_GUID, rand, player_version=PLAYER_VERSION, platform=PLATFORM)
    params = {
        'fp2p': 1,
        'charge': 0,
        'guid': PLAYER_GUID,
        'pid': PLAYER_PID,
        'vid': vid,
        'platform': PLATFORM,
        'cKey': ckey,
        'otype': 'xml', 
        'fhdswitch': 0,
        'defnpayver': 1,
        'appver': PLAYER_VERSION,
        'ehost': url, 
        'vids': vid,
        'encryptVer': '5.4',
        'utype': 0,
        'ran': '%.16f' % rand,
        'speed': random.randint(1000, 3000)
    }
    request = urllib2.Request('http://vv.video.qq.com/getvinfo')
    request.add_header('Referer', SWF_REFERER)
    request.add_header('Content-type', 'application/x-www-form-urlencoded')
    request.add_header('User-Agent', USER_AGENT)
    
    form = urllib.urlencode(params)
    resp = urllib2.urlopen(request, data=form)

    vinfo = resp.read()
    tree = etree.fromstring(vinfo)

    resolutions = {}
    slid = None
    for fi in tree.xpath('/root/fl/fi'):
        name = fi.xpath('name/text()')[0]
        fiid = int(fi.xpath('id/text()')[0])
        sl = int(fi.xpath('sl/text()')[0])
        cname = fi.xpath('cname/text()')[0]
        if sl:
            pass
        if name == 'fhd':
            slid = fiid
            print 'Selected %s: %s' % (name, cname)
        resolutions[name] = fiid

    print resolutions

    for vi in tree.xpath('/root/vl/vi'):
        video_type = int(vi.xpath('videotype/text()')[0])
        if video_type == 1:
            video_type = 'flv'
        elif video_type == 2:
            video_type = 'mp4'
        else:
            video_type = 'unknown'

        video_id = vi.xpath('vid/text()')[0]

        cdn_host = vi.xpath('ul/ui/url/text()')[0]
        vt = vi.xpath('ul/ui/vt/text()')[0]

        for ci in vi.xpath('cl/ci'):
            idx = int(ci.xpath('idx/text()')[0])
            cd = float(ci.xpath('cd/text()')[0])

            vclip = getvclip(url, vid, vt, slid, idx)

            filename = vclip['filename']
            key = vclip['key']

            print '%d: %s (%f, %d) %s' % (idx, filename, cd, vclip['fs'], vclip['md5'])

            cdn_url = '%s/%s' % (cdn_host, filename)
            target_file = os.path.join(target_dir, filename)
            if os.path.exists(target_file):
                continue
            download_vclip(target_file, cdn_url, key, vclip['br'], vclip['fmt'], vclip['fs'])


def getvclip(url, vid, vt, resolution, idx):
    rand = random.random()
    ckey = echo_ckeyv3(vid, PLAYER_GUID, rand, player_version=PLAYER_VERSION, platform=PLATFORM)
    params = {
        'buffer': 0,
        'guid': PLAYER_GUID,
        'vt': vt,
        'ltime': 77,
        'fmt': 'auto',
        'vid': vid,
        'platform': PLATFORM,
        'cKey': ckey,
        'format': resolution,
        'speed': random.randint(1000, 3000),
        'encryptVer': '5.4',
        'idx': idx,
        'appver': PLAYER_VERSION,
        'ehost': url,
        'dltype': 1,
        'charge': 0,
        'otype': 'xml',
        'ran': '%.16f' % rand
    }

    request = urllib2.Request('http://vv.video.qq.com/getvclip')
    request.add_header('Referer', SWF_REFERER)
    request.add_header('Content-type', 'application/x-www-form-urlencoded')
    request.add_header('User-Agent', USER_AGENT)
    
    form = urllib.urlencode(params)
    resp = urllib2.urlopen(request, data=form)

    vclip = resp.read()
    tree = etree.fromstring(vclip)

    vclip = {
        'filename': tree.xpath('/root/vi/fn/text()')[0],
        'br': float(tree.xpath('/root/vi/br/text()')[0]),
        'fmt': tree.xpath('/root/vi/fmt/text()')[0],
        'key': tree.xpath('/root/vi/key/text()')[0],
        'md5': tree.xpath('/root/vi/md5/text()')[0],
        'fs': int(tree.xpath('/root/vi/fs/text()')[0])
    }

    return vclip


def download_vclip(target_file, url, vkey, br, fmt, size, sp=0):
    params = {
        'sdtfrom': 'v1000',
        'type': 'mp4',
        'vkey': vkey,
        'platform': PLATFORM,
        'br': br,
        'fmt': fmt,
        'sp': sp,
        'guid': PLAYER_GUID
    }

    url = '%s?%s' % (url, urllib.urlencode(params))
    resp = urllib2.urlopen(url)

    start_time = time.time()
    downloaded_size = 0
    of = open(target_file, 'wb')
    while True:
        st = time.time()
        data = resp.read(128*1024)
        if not data:
            break
        of.write(data)
        downloaded_size += len(data)
        speed = (len(data)/1024)/(time.time() - st)
        percent = (downloaded_size * 100)/size
        print '[%d%%] %dKB/s %d/%d\r' % (percent, speed, downloaded_size, size),
        sys.stdout.flush()

    time_spent = time.time() - start_time
    speed = (downloaded_size/1024) / time_spent
    
    print 'Download %d bytes in %d seconds, speed %dKB/s' % (downloaded_size, time_spent, speed)

    of.close()


def get_suburl(browser, page_url, target_dir):
    print 'GET', page_url
    page = get_url(browser, page_url)
    scripts = page.xpath('//script')
    for script in scripts:
        if not script.text:
            continue
        if -1 != script.text.find('VIDEO_INFO'):
            break
    match = re.search('var\s+COVER_INFO\s?=\s?({[^;]+);', script.text)
    cover_info = to_dict(match.group(1))
    match = re.search('var\s+VIDEO_INFO\s?=\s?({[^;]+);', script.text)
    video_info = to_dict(match.group(1))
#    match = re.search('var\s+COVER_EX_INFO\s?=\s?({[^;]+);', script.text)
#    cover_ex_info = to_dict(match.group(1))
#    match = re.search('var\s+LANG_INFO\s?=\s?({[^;]+);', script.text)
#    lang_info = to_dict(match.group(1))
    print video_info['title']
    print 'Length:', video_info['duration']
    getvinfo(target_dir, page_url, video_info['vid'])


def txsp(page_url, target_dir):
    browser = Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [('User-Agent', USER_AGENT)]
    get_suburl(browser, page_url, target_dir)


if __name__ == '__main__':
    page_url = sys.argv[1]
    target_dir = sys.argv[2]
    txsp(page_url, target_dir)
