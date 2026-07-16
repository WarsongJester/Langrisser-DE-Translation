import struct
v=open('VDP2VRAM.bin','rb').read()
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
comp=d[offs[0]:offs[1]]
target=v[0x20000:0x20000+0x1c00]

class BR:
    def __init__(s,data,msb,start=0): s.d=data;s.i=start;s.nb=0;s.cur=0;s.msb=msb
    def bit(s):
        if s.nb==0: s.cur=s.d[s.i];s.i+=1;s.nb=8
        s.nb-=1
        return (s.cur>>s.nb)&1 if s.msb else (s.cur>>(7-s.nb))&1
    def bits(s,n):
        val=0
        for _ in range(n): val=(val<<1)|s.bit()
        return val

def decode(comp,msb,matchbit,skip,offbits,lenbits,lenadd,offfirst,rsize,rstart,relmode,maxlen):
    out=bytearray(); br=BR(comp,msb,skip)
    ring=bytearray(rsize); r=rstart%rsize
    try:
        while len(out)<maxlen:
            if br.bit()!=matchbit:
                c=br.bits(8); out.append(c); ring[r]=c; r=(r+1)%rsize
            else:
                if offfirst: o=br.bits(offbits); ln=br.bits(lenbits)+lenadd
                else: ln=br.bits(lenbits)+lenadd; o=br.bits(offbits)
                if relmode: pos=(r-o-1)%rsize
                else: pos=o%rsize
                for k in range(ln):
                    c=ring[(pos+k)%rsize]; out.append(c); ring[r]=c; r=(r+1)%rsize
    except (IndexError,): pass
    return bytes(out)

def matchlen(r):
    m=0
    for a,b in zip(r,target):
        if a==b:m+=1
        else:break
    return m

best=(0,None); cnt=0
for msb in (True,False):
 for matchbit in (0,1):
  for skip in (0,2):
   for offbits in (11,12):
    for lenbits in (4,5):
     for lenadd in (1,2,3):
      for offfirst in (True,False):
       for rsize in (4096,):
        for rstart in (0,rsize-offbits, 4078):
         for relmode in (True,False):
          cnt+=1
          r=decode(comp,msb,matchbit,skip,offbits,lenbits,lenadd,offfirst,rsize,rstart,relmode,len(target)+64)
          ml=matchlen(r)
          if ml>best[0]: best=(ml,(msb,matchbit,skip,offbits,lenbits,lenadd,offfirst,rstart,relmode,len(r)))
print('tested',cnt,'best',best[0],'of',len(target)); print(best[1])
