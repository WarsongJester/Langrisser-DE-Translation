from yss import load, chunks
import struct
def bswap(b):
    b=bytearray(b)
    if len(b)%2: b=bytes(b)+b'\x00'
    b=bytearray(b); b[0::2],b[1::2]=bytes(b[1::2]),bytes(b[0::2]); return bytes(b)

def state(path):
    d=load(path); cs=chunks(d)
    # HWRAM: OTHR payload start = CPU 0x06000000, byte-swapped, 1MB
    othr_off=cs['OTHR'][0][0]
    hwram=bswap(d[othr_off:othr_off+0x100000])   # CPU 0x06000000..0x06100000
    # LWRAM follows in OTHR after HWRAM (CPU 0x00200000), byte-swapped, 1MB
    lwram=bswap(d[othr_off+0x100000: othr_off+0x200000])
    # VDP2 VRAM: first 0x80000 of VDP2 payload
    v2_off=cs['VDP2'][0][0]
    vram_raw=d[v2_off:v2_off+0x80000]
    return dict(raw=d, cs=cs, hwram=hwram, lwram=lwram, vram_raw=vram_raw)

def hw(st, cpu, n):
    o=cpu-0x06000000
    return st['hwram'][o:o+n]

if __name__=='__main__':
    st=state('/mnt/user-data/uploads/commandring.yss')
    lang1=open('jp/LANG1.BIN','rb').read()
    # verify HWRAM holds LANG1 verbatim at 0x06010000
    a=st['hwram'][0x10000:0x10000+0x40]
    b=lang1[0:0x40]
    print('LANG1 verbatim at HWRAM 0x06010000?', a==b)
    # show classpool to confirm
    cp=hw(st,0x060717AC,32)
    print('classpool@0x060717AC bytes:', cp.hex())
