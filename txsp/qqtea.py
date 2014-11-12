#!/usr/bin/env python

import base64
import struct


def pack(data):
    target = []
    target.extend(struct.pack('>I', data[0]))
    target.extend(struct.pack('>I', data[1]))
    target = [ord(c) for c in target]
    return target


def unpack(data):
    data = ''.join([chr(b) for b in data])
    target = []
    target.extend(struct.unpack('>I', data[:4]))
    target.extend(struct.unpack('>I', data[4:8]))
    return target


def tea_encrypt(v, key):
    delta = 0x9e3779b9
    s = 0
    v = unpack(v)
    rounds = 16
    while rounds:
        s += delta
        s &= 0xffffffff
        v[0] += (v[1]+s) ^ ((v[1]>>5)+key[1]) ^ ((v[1]<<4)+key[0])
        v[0] &= 0xffffffff
        v[1] += (v[0]+s) ^ ((v[0]>>5)+key[3]) ^ ((v[0]<<4)+key[2])
        v[1] &= 0xffffffff
        rounds = rounds - 1
    return pack(v)


def qq_encrypt(data, key):
    temp = [0x00]*8
    enc = tea_encrypt(data, key)
    for i in range(8, len(data), 8):
        d1 = data[i:]
        for j in range(8):
            d1[j] = d1[j] ^ enc[i+j-8]
        d1 = tea_encrypt(d1, key)
        for j in range(len(d1)):
            d1[j] = d1[j]^data[i+j-8]^temp[j]
            enc.append(d1[j])
            temp[j] = enc[i+j-8]
    return enc


def strsum(data):
    s = 0
    for c in data:
        s = s*131 + ord(c)
    return 0x7fffffff & s


# seed = 0xdead
# 
# def randint():
#     global seed
# 
#     if seed == 0:
#         seed = 123459876
# 
#     k1 = -2836 * (seed / 127773)
#     k2 = 16807 * (seed % 127773)
# 
#     seed = k1 + k2
#     if seed < 0:
#         seed = seed + 2147483647
#     return seed


def ccc(platform, version, timestamp):
    key = [1735078436, 1281895718, 1815356193, 879325047]
    s1 = '537e6f0425c50d7a711f4af6af719e05d41d8cd98f00b204e9800998ecf8427e8afc2cf649f5c36c4fa3850ff01c1863d41d8cd98100b204e9810998ecf84271'
    d = [0x3039, 0x02]
    d.append(timestamp)
    d.append(platform)
    d.append(strsum(version))
    d.append(strsum(s1))
    data = [0xa6, 0xf1, 0xd9, 0x2a, 0x82, 0xc8, 0xd8, 0xfe, 0x43]
    for i in d:
        data.extend([ord(c) for c in struct.pack('>I', i)])
    data.extend([0x00]*7)

    # for d in data:
    #     print '%02x' % d,
    # print
    enc = qq_encrypt(data, key)
    return base64.b64encode(''.join([chr(b) for b in enc]), '_-').replace('=', '')


if __name__ == '__main__':
    print ccc(2, "9.2.18.285", 0)
