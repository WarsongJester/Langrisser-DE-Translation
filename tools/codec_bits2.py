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

def decode(comp,msb,matchbit,skip,offbits,lenbits,lenadd,offfirst,maxlen,trace=False):
    out=bytearray(); br=BR(comp,msb,skip); ops=[]
    try:
        while len(out)<maxlen:
            fb=br.bit()
            if fb!=matchbit:
                c=br.bits(8); out.append(c)
                if trace and len(ops)<20: ops.append(('L',c,len(out)))
            else:
                if offfirst: off=br.bits(offbits); ln=br.bits(lenbits)+lenadd
                else: ln=br.bits(lenbits)+lenadd; off=br.bits(offbits)
                st=len(out)-off
                for k in range(ln):
                    out.append(out[st+k] if 0<=st+k<len(out) else 0)
                if trace and len(ops)<20: ops.append(('M',off,ln,len(out)))
    except (IndexError,): pass
    return bytes(out),ops

def matchlen(r):
    m=0
    for a,b in zip(r,target):
        if a==b:m+=1
        else:break
    return m

best=(0,None)
for msb in (True,False):
 for matchbit in (0,1):
  for skip in (0,2):
   for offbits in (10,11,12,13):
    for lenbits in (4,5,6,7,8):
     for lenadd in (1,2,3):
      for offfirst in (True,False):
       r,_=decode(comp,msb,matchbit,skip,offbits,lenbits,lenadd,offfirst,len(target)+64)
       ml=matchlen(r)
       if ml>best[0]: best=(ml,(msb,matchbit,skip,offbits,lenbits,lenadd,offfirst,len(r)))
print('best',best[0],'of',len(target)); print(best[1])
if best[1]:
    cfg=best[1]
    r,ops=decode(comp,cfg[0],cfg[1],cfg[2],cfg[3],cfg[4],cfg[5],cfg[6],len(target)+64,trace=True)
    print('trace:',ops[:15])
    print('decoded[30:40]',r[30:40].hex(),'target[30:40]',target[30:40].hex())
