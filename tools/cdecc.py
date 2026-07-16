# CD-ROM Mode 1 (2352) EDC/ECC, validated byte-identical vs original disc.
import struct
def _edc_table():
    t=[]
    for i in range(256):
        c=i
        for _ in range(8): c=(c>>1)^(0xD8018001 & -(c&1))
        t.append(c&0xFFFFFFFF)
    return t
_EDCT=_edc_table()
def edc(data):
    c=0
    for b in data: c=_EDCT[(c^b)&0xFF]^(c>>8)
    return c&0xFFFFFFFF
_F=[0]*256; _B=[0]*256
for i in range(256):
    j=((i<<1)^(0x11D if (i&0x80) else 0))&0xFF
    _F[i]=j; _B[(i^j)&0xFF]=i
def _block(src, major_count, minor_count, major_mult, minor_inc, dst, doff):
    size=major_count*minor_count
    for major in range(major_count):
        index=(major>>1)*major_mult+(major&1)
        a=0; b=0
        for minor in range(minor_count):
            t=src[index]; index+=minor_inc
            if index>=size: index-=size
            a^=t; b^=t; a=_F[a]
        a=_B[(_F[a]^b)&0xFF]
        dst[doff+major]=a
        dst[doff+major+major_count]=(a^b)&0xFF
def reframe(sector2352, lba):
    s=bytearray(sector2352)
    # sync
    s[0:12]=bytes([0,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0xff,0])
    # header MSF (BCD) for lba (lba+150 -> MSF)
    a=lba+150
    m=a//(60*75); sec=(a//75)%60; fr=a%75
    def bcd(x): return ((x//10)<<4)|(x%10)
    s[12]=bcd(m); s[13]=bcd(sec); s[14]=bcd(fr); s[15]=0x01
    # EDC over 0x000..0x80F
    e=edc(bytes(s[0:0x810]))
    s[0x810:0x814]=struct.pack('<I',e)
    # intermediate zero
    for i in range(0x814,0x81C): s[i]=0
    # ECC over src starting at 0x0C
    _block(s[0x0C:],86,24,2,86,s,0x81C)        # P (P does not read its own parity region)
    _block(s[0x0C:],52,43,86,88,s,0x8C8)       # Q (re-slice AFTER P so Q includes updated P)
    return bytes(s)
