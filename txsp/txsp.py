#!/usr/bin/env python

from mechanize import Browser
from lxml import etree, html

import datetime
import json
import os
import random
import re
import socket
import sys
import time
import urllib
import urllib2
import uuid

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0'
SWF_REFERER = 'https://imgcache.qq.com/tencentvideo_v1/playerv3/TencentPlayer.swf?max_age=86400&v=20170106'
PLATFORM = 10902
PLAYER_GUID = uuid.uuid4().hex.upper()
PLAYER_PID = uuid.uuid4().hex.upper()
PLAYER_VERSION = '3.2.33.397'

REMOTE_TOKEN = ''


def kvcollect(url, cmid, vid, pid):

    ctime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %f')[:-3]
    data = {
        'bufferwait': 0, 'level': 0, 'step': 3, 'tpay': '',
        'url': url,
        'predefn': 0,
        'pid': pid,
        'isvisible': 1, 'isfocustab': 1, 'bt': 0, 'ctime': ctime,
        'type': 0, 'platform': 11, 'cpay': 0, 'rcd_info': '',
        'cmid': cmid,
        'ptag': '',
        'pfversion': 'MAC.24.0',
        'ua': USER_AGENT,
        'ispac': 0, 'clspeed': 0, 'preformat': 0, 'rid': '', 'pversion': '',
        'vid': vid,
        'exid': 0, 'adid': '', 'BossId': 2577, 'hc_uin': '',
        'hc_main_login': '', 'version': 'TencentPlayerV%s' % PLAYER_VERSION, 
        'v_idx': 0, 'hc_vuserid': '', 'encv': 0, 'hc_openid': '', 'hc_appid': '', 
        'autoformat': 1, 'hc_qq': 0, 'head_ref': '', 'buffersize': 0, 'tpid': 3,
        'loadwait': 0, 'vt': 0, 'index': 0, 'val2': 0, 'idx': 0, 'iformat': '', 
        'isvip': -1, 'emsg': '', 'bi': 0, 'val1': 0, 'val': 1, 'ptime': 0,
        'vurl': '', 'diaonlen': 1020, 'dltype': 1, 'defn':''
    }
    data = urllib.urlencode(data)
    request = urllib2.Request('https://btrace.video.qq.com/kvcollect')
    request.add_header('User-Agent', USER_AGENT)
    resp = urllib2.urlopen(request, data=data)
    print resp.read()


def get_remote_token(token):
    sock = socket.socket()
    sock.connect(('rlog.video.qq.com', 8080))
    for i in range(0, len(token), 2):
        c = token[i:i+2]
        d = chr(int(c, 16))
        sock.send(d)
    data = sock.recv(200)
    l = ord(data[0]) | ord(data[1])<<8
    assert l + 2 == len(data)
    rtoken = []
    loc5 = [96,71,147,86]
    for i in range(0, l):
        c = ord(data[i+2]) ^ loc5[i%4]
        rtoken.append(chr(c))

    return ''.join(rtoken)
    

def sandbox_api(t, **params):
    req = {
        'type': t,
    }
    req.update(**params)
    qs = urllib.urlencode(req)
    url = 'http://sandbox.xinfan.org/cgi-bin/txsp/ckey54?' + qs
    resp = urllib2.urlopen(url)
    return json.load(resp).get('result')


def get_rtoken(user_id, platform, player_version):
    global REMOTE_TOKEN
    if not REMOTE_TOKEN:
        print 'Guid:', user_id
        token = sandbox_api('token', guid=user_id, platform=platform, player_version=player_version)
        REMOTE_TOKEN = get_remote_token(token)
        print 'Remote Token:', REMOTE_TOKEN
    return REMOTE_TOKEN


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


def loadKey(rtoken, vid, stdfrom):
    time_url = 'https://vv.video.qq.com/checktime?ran=%.16f' % random.random()
    request = urllib2.Request(time_url)
    resp = urllib2.urlopen(request)
    body = resp.read()
    # <?xml version="1.0" encoding="utf-8"  standalone="no" ?>
    # <root><s>o</s><t>1483845096</t><ip>39.184.134.237</ip><pos></pos><rand>QwRdjlvpMb0bpPWxNWGXZw==</rand></root>
    tree = etree.fromstring(body)
    timestamp = tree.xpath('/root/t/text()')[0]
    ip = tree.xpath('/root/ip/text()')[0]
    rand = tree.xpath('/root/rand/text()')[0]

    stdfrom_2_fd = {
   	'v1040': 'bcig',
        'v1000': 'bceg',
        'v1021': 'bcgh',
        'v1022': 'bcgi',
        'v1023': 'bcgj',
        'v1024': 'bcgk',
        'v1050': 'bcjg',
        'v1045': 'bcil',
        'v1025': 'bcgl',
        'v1070': 'bclg',
        'v1071': 'bclh',
        'v1091': 'bcnh',
        'v1090': 'bcng',
        'v1080': 'bcmg',
        'v1031': 'bchh',
        'v1032': 'bchi',
        'v1001': 'bceh',
        'v1070': 'bclg' 
    }

    params = {
        'rtoken': rtoken,
        'platform': PLATFORM,
        'version': '5.4',
        'player_version': PLAYER_VERSION,
        'vid': vid,
        'timestamp': int(timestamp),
        'rand': rand,
        'sd': stdfrom_2_fd.get(stdfrom, ''),
        'guid': PLAYER_GUID,
    }

    ckey = sandbox_api('ckey', **params)

    return ckey


def getvinfo(target_dir, url, vid):
    rtoken = get_rtoken(PLAYER_GUID, PLATFORM, PLAYER_VERSION)
    ckey = loadKey(rtoken, vid, 'v1000')

    rand = random.random()
    params = {
        'vid': vid,
        'linkver': 2,
        'otype': 'xml', 
        'defnpayver': 1,
        'platform': PLATFORM,
        'newplatform': PLATFORM,
        'charge': 0,
        'ran': '%.16f' % rand,
        'speed': random.randint(5000, 9000),
        'defaultfmt': 'shd',
        'pid': PLAYER_PID,
        'appver': PLAYER_VERSION,
        'fhdswitch': 0,
        'guid': PLAYER_GUID,
        'ehost': url, 
        'dtype': 3,
        'fp2p': 1,
        'cKey': ckey,
        'utype': 0,
        'encryptVer': '5.4',
        'ip': '',
        'defn': 'shd',
        'sphls': 1,
        'refer': '',
        'drm': 8,
        'sphttps': 1
    }

    request = urllib2.Request('https://vv.video.qq.com/getvinfo')
    request.add_header('Referer', SWF_REFERER)
    request.add_header('Content-type', 'application/x-www-form-urlencoded')
    request.add_header('User-Agent', USER_AGENT)
    
    form = urllib.urlencode(params)
    resp = urllib2.urlopen(request, data=form)

    vinfo = resp.read()
    tree = etree.fromstring(vinfo)

    resolutions = {}
    slid = None
    slname = None
    for fi in tree.xpath('/root/fl/fi'):
        name = fi.xpath('name/text()')[0]
        fiid = int(fi.xpath('id/text()')[0])
        sl = int(fi.xpath('sl/text()')[0])
        cname = fi.xpath('cname/text()')[0]
        resolutions[name] = fiid
        if sl: #name in ('shd', 'fhd'):
            slid = fiid
            slname = name
            print 'Selected %s: %s' % (name, cname)
            break

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
        fn = vi.xpath('fn/text()')[0]
        fs = int(vi.xpath('fs/text()')[0])
        lnk = vi.xpath('lnk/text()')[0]
        br = vi.xpath('br/text()')[0]

        fc = int(vi.xpath('cl/fc/text()')[0])
        if fc == 0:
            filename = ''
            vkey = getvkey(url, vid, vt, slid, fn, lnk)
            filename = vkey.get('filename')
            target_file = os.path.join(target_dir, filename)
            cdn_url = '%s/%s' % (cdn_host, filename)
            key = vkey.get('key')
            br = vkey.get('br')
            download_vclip(target_file, cdn_url, key, br, video_type, fs)

        else:
            for ci in vi.xpath('cl/ci'):
                idx = int(ci.xpath('idx/text()')[0])
                cd = float(ci.xpath('cd/text()')[0])
                md5 = ci.xpath('cmd5/text()')[0]
                vclip = getvclip(url, vid, vt, slid, idx, slname, lnk)

                filename = vclip['filename']
                key = vclip['key']

                print '%d: %s (%f, %d) %s' % (idx, filename, cd, vclip['fs'], md5)

                cdn_url = '%s%s' % (cdn_host, filename)
                target_file = os.path.join(target_dir, filename)
                if os.path.exists(target_file):
                    continue
                download_vclip(target_file, cdn_url, key, vclip['br'], vclip['fmt'], vclip['fs'])


def getvkey(url, vid, vt, resolution, filename, lnk):

    rtoken = get_rtoken(PLAYER_GUID, PLATFORM, PLAYER_VERSION)
    ckey = loadKey(rtoken, vid, 'v1000')

    rand = random.random()

    params = {
        'vid': vid,
        'lnk': lnk,
        'linkver': 2,
        'otype': 'xml',
        'platform': PLATFORM,
        'format': resolution,
        'charge': 0,
        'ran': '%.16f' % rand,
        'filename': filename,
        'vt': vt,
        'appver': PLAYER_VERSION,
        'guid': PLAYER_GUID,
        'cKey': ckey,
        'encryptVer': '5.4',
        'ehost': url,
        'auth_from': 'undefined'
    }

    request = urllib2.Request('https://vv.video.qq.com/getvkey')
    request.add_header('Referer', SWF_REFERER)
    request.add_header('Content-type', 'application/x-www-form-urlencoded')
    request.add_header('User-Agent', USER_AGENT)
    
    form = urllib.urlencode(params)
    resp = urllib2.urlopen(request, data=form)
    resp_body = resp.read()
    tree = etree.fromstring(resp_body)
    vkey = {
        'filename': tree.xpath('/root/keyid/text()')[0] + '.mp4',
        'br': float(tree.xpath('/root/br/text()')[0]),
        'key': tree.xpath('/root/key/text()')[0]
    }
    return vkey


def getvclip(url, vid, vt, resolution, idx, fmt, lnk):
    rtoken = get_rtoken(PLAYER_GUID, PLATFORM, PLAYER_VERSION)
    ckey = loadKey(rtoken, vid, 'v1000')

    rand = random.random()

    params = {
        'cKey': ckey,
        'ltime': 0,
        'appver': PLAYER_VERSION,
        'fmt': fmt,
        'format': resolution,
        'linkver': 2,
        'encryptVer': '5.4',
        'ran': '%.16f' % rand,
        'otype': 'xml',
        'lnk': lnk,
        'idx': idx,
        'platform': PLATFORM,
        'charge': 0,
        'vt': vt,
        'speed': random.randint(1000, 3000),
        'buffer': 0,
        'guid': PLAYER_GUID,
        'ehost': url,
        'vid': vid,
        'dltype': 1,
    }

    request = urllib2.Request('https://vv.video.qq.com/getvclip')
    request.add_header('Referer', SWF_REFERER)
    request.add_header('Content-type', 'application/x-www-form-urlencoded')
    request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
    request.add_header('User-Agent', USER_AGENT)
    
    form = urllib.urlencode(params)
    resp = urllib2.urlopen(request, data=form)

    vclip = resp.read()
    tree = etree.fromstring(vclip)

    vclip = {
        'filename': tree.xpath('/root/vi/fn/text()')[0],
        'br': int(tree.xpath('/root/vi/br/text()')[0]),
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
        'guid': PLAYER_GUID,
        'level': 0
    }

    url = '%s?%s' % (url, urllib.urlencode(params))
    print url
    request = urllib2.Request(url)
    request.add_header('User-Agent', USER_AGENT)
    resp = urllib2.urlopen(request)

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

    kvcollect(page_url, PLAYER_GUID, video_info['vid'], PLAYER_PID)

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
