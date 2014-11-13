#!/usr/bin/env python

from mechanize import Browser
from lxml import etree, html

import os
import random
import re
import sys
import time
import urllib
import uuid

from qqtea import ccc

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:33.0) Gecko/20100101 Firefox/33.0'
SWF_REFERER = 'http://imgcache.qq.com/tencentvideo_v1/player/TencentPlayer.swf?max_age=86400&v=20140917'
PLAYER_PLATFORM = 11
PLAYER_VERSION = '3.2.18.285'
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

def load_key(browser):
    url = 'http://vv.video.qq.com/checktime'
    resp = browser.open(url)
    xml = etree.fromstring(resp.read())
    t = int(xml.xpath('/root/t/text()')[0])

    return ccc(PLAYER_PLATFORM, PLAYER_VERSION, t)

def get_user_agent(vid, fmt):
    ua = 'Mozilla/5.0 TencentPlayerVod_1.1.91 tencent_-%s-%s' % (vid, fmt)
    return ua

def get_from(url):
    return 'v1001'

def download_clip(target_file, size, user_agent, url, fmt_name, type_name, br, sp, vkey, level):
    browser = Browser()
    browser.set_handle_robots(False)

    form = {
        'stdfrom': get_from(url),
        'type': type_name,
        'vkey': vkey,
        'level': level,
        'platform': PLAYER_PLATFORM,
        'br': br,
        'fmt': fmt_name,
        'sp': sp,
    }

    query_string = urllib.urlencode(form)
    browser.addheaers = [
        ('User-Agent', user_agent),
        ('x-flash-version', 'MAC 15,0,0,189')]

    resp = browser.open('%s?%s' % (url, query_string))

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
        print '[%%%d] %dKB/s %d/%d\r' % (percent, speed, downloaded_size, size),
        sys.stdout.flush()

    time_spent = time.time() - start_time
    speed = (downloaded_size/1024) / time_spent
    
    print 'Download %d bytes in %d seconds, speed %dKB/s' % (downloaded_size, time_spent, speed)

    of.close()

def get_videoinfo(browser, target_dir, vid):
    browser.addheaders = [('User-Agent', USER_AGENT), ('Referer', SWF_REFERER)]
    player_pid = uuid.uuid4().hex.upper()
    params = {
        'vids': vid,
        'vid': vid,
        'otype': 'xml',
        'defnpayver': 1,
        'platform': PLAYER_PLATFORM,
        'charge': 0,
        'ran': random.random(),
        'speed': random.randint(2048, 8096),
        'pid': player_pid,
        'appver': PLAYER_VERSION,
        'fhdswitch': 0,
        'fp2p': 1,
        'utype': 0,
        'cKey': load_key(browser),
        'encryptVer': KLIB_VERSION,
    }

    form = urllib.urlencode(params)
    resp = browser.open('http://vv.video.qq.com/getvinfo', data=form)
    vinfo = resp.read()
    # print vinfo
    open('a.xml', 'wb').write(vinfo)
    tree = etree.fromstring(vinfo)

    fmt_id = None
    fmt_name = None
    fmt_br = None
    for fmt in tree.xpath('/root/fl/fi'):
        sl = int(fmt.xpath('sl/text()')[0])
        if sl:
            fmt_id = fmt.xpath('id/text()')[0]
            fmt_name = fmt.xpath('name/text()')[0]
            fmt_br = fmt.xpath('br/text()')[0]

    assert fmt_id

    video = tree.xpath('/root/vl/vi')[0]
    filename = video.xpath('fn/text()')[0]
    filesize = video.xpath('fs/text()')[0]

    cdn = video.xpath('ul/ui')[0]
    cdn_url = cdn.xpath('url/text()')[0]
    filetype = int(cdn.xpath('dt/text()')[0])
    vt = cdn.xpath('vt/text()')[0]

    if filetype == 1:
        type_name = 'flv'
    elif filetype == 2:
        type_name = 'mp4'
    else:
        type_name = 'unknown'

    clips = []
    for ci in video.xpath('cl/ci'):
        clip_size = int(ci.xpath('cs/text()')[0])
        clip_idx = int(ci.xpath('idx/text()')[0])
        clips.append({'idx': clip_idx, 'size': clip_size})

    print 'File name:', filename
    print 'Size: %s (%s) in %d clips:' % (filesize, fmt_name, len(clips)),
    for clip in clips:
        print clip['size'],
    print

    user_agent = 'Mozilla/5.0 TencentPlayerVod_1.1.91 tencent_-%s-%s' % (vid, fmt_id)

    fns = os.path.splitext(filename)

    for clip in clips:
        fn = '%s.%d%s' % (fns[0], clip['idx'], fns[1])

        params = {
            'vid': vid,
            'otype': 'xml',
            'platform': PLAYER_PLATFORM,
            'format': fmt_id,
            'charge': 0,
            'ran': random.random(),
            'filename': fn,
            'vt': vt,
            'appver': PLAYER_VERSION,
            'cKey': load_key(browser),
            'encryptVer': KLIB_VERSION,
        }
        form = urllib.urlencode(params)
        #print form
        resp = browser.open('http://vv.video.qq.com/getvkey', data=form)
        vkey_body = resp.read()
        #print vkey_body
        tree = etree.fromstring(vkey_body)

        vkey = tree.xpath('/root/key/text()')[0]
        level = tree.xpath('/root/level/text()')[0]
        sp = tree.xpath('/root/sp/text()')[0]

        clip_size = clip['size']
        clip_url = '%s%s' % (cdn_url, fn)
        clip_file = os.path.join(target_dir, fn)

        print 'Clip %s, size %d' % (fn, clip_size), clip_url
        print 'Save to', clip_file
        download_clip(clip_file, clip_size, user_agent, clip_url, fmt_name, type_name, fmt_br, sp, vkey, level)

def get_suburl(browser, page_url, target_dir):
    print 'GET', page_url
    page = get_url(browser, page_url)
    scripts = page.xpath('/html/head/script')
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
    get_videoinfo(browser, target_dir, video_info['vid'])

def txsp(page_url, target_dir):
    browser = Browser()
    browser.set_handle_robots(False)
    browser.addheaders = [('User-Agent', USER_AGENT)]
    get_suburl(browser, page_url, target_dir)

if __name__ == '__main__':
    page_url = sys.argv[1]
    target_dir = sys.argv[2]
    txsp(page_url, target_dir)
