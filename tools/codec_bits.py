import struct
v=open('VDP2VRAM.bin','rb').read()
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
comp=d[offs[0]:offs[1]]
target=v[0x20000:0x20000+0x1c00]

class BR:
    def __init__(s,data,msb,start=0):
        s.d=data; s.i=start; s.nb=0; s.cur=0; s.msb=msb
    def bit(s):
        if s.nb==0:
            s.cur=s.d[s.i]; s.i+=1; s.nb=8
        s.nb-=1
        return (s.cur>>s.nb)&1 if s.msb else (s.cur>>(7-s.nb))&1
    def bits(s,n):
        val=0
        for _ in range(n):
            val=(val<<1)|s.bit()
        return val

def decode(comp,msb,lit1,skip,offbits,lenbits,lenadd,offfirst,maxlen):
    out=bytearray()
    br=BR(comp,msb,skip)
    try:
        while len(out)<maxlen:
            if (br.bit()==1)==lit1:
                out.append(br.bits(8))
            else:
                if offfirst:
                    off=br.bits(offbits); ln=br.bits(lenbits)+lenadd
                else:
                    ln=br.bits(lenbits)+lenadd; off=br.bits(offbits)
                if off==0: off=1
                start=len(out)-off
                for k in range(ln):
                    out.append(out[start+k] if 0<=start+k<len(out) else 0)
    except (IndexError,):
        pass
    return bytes(out)

def matchlen(r):
    m=0
    for a,b in zip(r,target):
        if a==b: m+=1
        else: break
    return m

best=(0,None)
for msb in (True,False):
 for lit1 in (True,False):
  for skip in (0,2,4):
   for offbits in (8,9,10,11,12,13):
    for lenbits in (3,4,5):
     for lenadd in (1,2,3):
      for offfirst in (True,False):
       r=decode(comp,msb,lit1,skip,offbits,lenbits,lenadd,offfirst,len(target)+64)
       ml=matchlen(r)
       if ml>best[0]:
        best=(ml,(msb,lit1,skip,offbits,lenbits,lenadd,offfirst,len(r)))
print('best',best[0],'of',len(target))
print(best[1])
