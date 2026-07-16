import struct
v=open('VDP2VRAM.bin','rb').read()
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
comp=d[offs[0]:offs[1]]
target=v[0x20000:0x22000]
def bitarr(data,msb):
    o=[]
    for byte in data:
        for k in range(8): o.append((byte>>(7-k))&1 if msb else (byte>>k)&1)
    return o
def run(ba,matchbit,offbits,lenbits,thr,offfirst):
    def rd(pos,n):
        val=0
        for k in range(n): val=(val<<1)|ba[pos+k]
        return val
    pos=0; out=bytearray()
    L=len(ba)
    while pos+1<L and len(out)<len(target):
        f=ba[pos]; pos+=1
        if f!=matchbit:
            if pos+8>L: break
            out.append(rd(pos,8)); pos+=8
        else:
            if offfirst:
                if pos+offbits+lenbits>L: break
                o=rd(pos,offbits); pos+=offbits; l=rd(pos,lenbits); pos+=lenbits
            else:
                if pos+offbits+lenbits>L: break
                l=rd(pos,lenbits); pos+=lenbits; o=rd(pos,offbits); pos+=offbits
            ln=l+thr; st=len(out)-o
            for k in range(ln):
                out.append(out[st+k] if 0<=st+k<len(out) else 0)
    m=0
    for a,b in zip(out,target):
        if a==b: m+=1
        else: break
    return m
best=[]
for msb in (True,False):
    ba=bitarr(comp,msb)
    for matchbit in (0,1):
        for offbits in range(7,15):
            for lenbits in range(2,11):
                for thr in (0,1,2,3):
                    for offfirst in (True,False):
                        m=run(ba,matchbit,offbits,lenbits,thr,offfirst)
                        best.append((m,(msb,matchbit,offbits,lenbits,thr,offfirst)))
best.sort(reverse=True)
for m,c in best[:12]: print(m,c)
