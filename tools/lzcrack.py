import struct
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
assets=[d[offs[i]:(offs[i+1] if i+1<207 else len(d))] for i in range(207)]

class Bits:
    def __init__(s,data,msb=True): s.d=data; s.i=0; s.bit=0; s.msb=msb; s.cur=0
    def getbit(s):
        if s.bit==0:
            if s.i>=len(s.d): raise EOFError
            s.cur=s.d[s.i]; s.i+=1; s.bit=8
        s.bit-=1
        if s.msb: b=(s.cur>>s.bit)&1
        else: b=(s.cur>>(7-s.bit))&1
        return b
    def getbyte(s):
        if s.i>=len(s.d): raise EOFError
        v=s.d[s.i]; s.i+=1; return v

def try_lzss(data, msb, lit_is_one, off_bits, len_bits, len_add, ring_size, ring_init, off_from_pos):
    # generic ring-buffer LZSS
    out=bytearray()
    ring=bytearray([ring_init])*ring_size
    rp=ring_size - 18 if ring_size>18 else 0
    b=Bits(data,msb)
    try:
        while True:
            flag=b.getbit()
            islit = (flag==1)==lit_is_one
            if islit:
                v=b.getbyte(); out.append(v); ring[rp%ring_size]=v; rp+=1
            else:
                hi=b.getbyte(); lo=b.getbyte()
                # pack offset/length
                if off_bits==12 and len_bits==4:
                    off=hi | ((lo&0xf0)<<4); ln=(lo&0x0f)+len_add
                elif off_bits==8 and len_bits==8:
                    off=hi; ln=lo+len_add
                else:
                    return None
                for k in range(ln):
                    if off_from_pos:
                        src=(rp-off)%ring_size
                    else:
                        src=off%ring_size; off+=0  # absolute window
                    c=ring[(src+k)%ring_size] if off_from_pos else ring[(off+k)%ring_size]
                    out.append(c); ring[rp%ring_size]=c; rp+=1
            if b.i>=len(data) and b.bit==0:
                break
            if len(out)>200000: return None
    except EOFError:
        pass
    return bytes(out)

# Validator: fully consumes input, sensible output. Test across many assets.
import itertools
configs=[]
for msb in (True,False):
  for lit_is_one in (True,False):
    for (ob,lb,la) in [(12,4,3),(12,4,2),(12,4,1),(8,8,1),(8,8,2)]:
      for rinit in (0x00,0x20):
        configs.append((msb,lit_is_one,ob,lb,la,4096,rinit,True))

test_idx=[0,13,32,38,100,150,206]
best=None
for cfg in configs:
    ok=0; sizes=[]
    for ti in test_idx:
        r=try_lzss(assets[ti],*cfg)
        if r is None: sizes.append(-1); continue
        sizes.append(len(r)); ok+=1
    print(cfg[:5], cfg[6], 'sizes',sizes)
