#!/usr/bin/env python

import struct

DELTA = 0x9e3779b9
ROUNDS = 16

SALT_LEN = 2
ZERO_LEN = 7

SEED = 0xdead


def rand():
    global SEED
    if SEED == 0:
        SEED = 123459876

    k1 = 0xffffffff & (-2836 * (SEED / 127773))
    k2 = 0xffffffff & (16807 * (SEED % 127773))

    SEED = 0xffffffff & (k1 + k2)
    if SEED < 0:
        SEED = SEED + 2147483647
    return SEED


def pack(data):
    target = []
    for i in data:
        target.extend(struct.pack('>I', i))
    target = [ord(c) for c in target]
    return target


def unpack(data):
    data = ''.join([chr(b) for b in data])
    target = []
    for i in range(0, len(data), 4):
        target.extend(struct.unpack('>I', data[i:i+4]))
    return target


def tea_encrypt(v, key):
    s = 0
    key = unpack(key)
    v = unpack(v)
    for i in range(ROUNDS):
        s += DELTA
        s &= 0xffffffff
        v[0] += (v[1]+s) ^ ((v[1]>>5)+key[1]) ^ ((v[1]<<4)+key[0])
        v[0] &= 0xffffffff
        v[1] += (v[0]+s) ^ ((v[0]>>5)+key[3]) ^ ((v[0]<<4)+key[2])
        v[1] &= 0xffffffff
    return pack(v)


def oi_symmetry_encrypt2(raw_data, key):
    pad_salt_body_zero_len = 1 + SALT_LEN + len(raw_data) + ZERO_LEN

    pad_len = pad_salt_body_zero_len % 8

    if pad_len:
        pad_len = 8 - pad_len

    data = []
    data.append(rand() & 0xf8 | pad_len)

    while pad_len + SALT_LEN:
        data.append(rand() & 0xff)
        pad_len = pad_len - 1

    data.extend(raw_data)
    data.extend([0x00] * ZERO_LEN)

    temp = [0x00] * 8

    enc = tea_encrypt(data[:8], key)
    for i in range(8, len(data), 8):
        d1 = data[i:]
        for j in range(8):
            d1[j] = d1[j] ^ enc[i-8+j]
        d1 = tea_encrypt(d1, key)
        for j in range(8):
            d1[j] = d1[j] ^ data[i-8+j] ^ temp[j]
            enc.append(d1[j])
            temp[j] = enc[i-8+j]

    return enc


if __name__ == '__main__':
    def print_hex(d):
        for i in range(len(d)):
            print '0x%02X,' % d[i],
            if i and not (i+1) % 16:
                print 

        print

    data = [ 
        0x00, 0x70, 0x00, 0x00, 0x54, 0x03, 0xBC, 0xDB, 
        0x40, 0xBA, 0x00, 0x00, 0x2A, 0x96, 0x00, 0x0D,
        0xF8, 0x9B, 0x56, 0x03, 0xC1, 0x97, 0x00, 0x04, 
        0x62, 0x63, 0x6E, 0x67, 0x00, 0x00, 0x00, 0x0A,
        0x33, 0x2E, 0x32, 0x2E, 0x31, 0x39, 0x2E, 0x33, 
        0x33, 0x34, 0x00, 0x0B, 0x35, 0x4F, 0x30, 0x55,
        0x35, 0x74, 0x76, 0x36, 0x74, 0x75, 0x56, 0x00, 
        0x29, 0x32, 0x39, 0x34, 0x33, 0x39, 0x38, 0x45,
        0x39, 0x44, 0x36, 0x30, 0x30, 0x45, 0x44, 0x34, 
        0x34, 0x35, 0x32, 0x45, 0x41, 0x44, 0x34, 0x41,
        0x39, 0x33, 0x35, 0x37, 0x34, 0x41, 0x31, 0x31, 
        0x38, 0x39, 0x39, 0x34, 0x43, 0x30, 0x31, 0x32,
        0x43, 0x35, 0x1F, 0xA5, 0x3B, 0xDB, 0x1F, 0xA5, 
        0x3B, 0xDB, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00,
        0x00, 0x00
    ]
    key = [
        0xfa, 0x82, 0xde, 0xb5, 0x2d, 0x4b, 0xba, 0x31, 
        0x39, 0x6,  0x33, 0xee, 0xfb, 0xbf, 0xf3, 0xb6
    ]
    print_hex(key)
    print_hex(data)
    enc = oi_symmetry_encrypt2(data, key)
    print_hex(enc)
