import struct
v=open('VDP2VRAM.bin','rb').read()
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
comp=d[offs[0]:offs[1]]
target=v[0x20000:0x20000+0x1c00]

def matchlen(r):
    m=0
    for a,b in zip(r,target):
        if a==b: m+=1
        else: break
    return m

# Classic byte-aligned LZSS with ring buffer
def lzss_classic(comp, skip, rsize, rinit, rstart, lit_is_1, thr, pack, msbflag):
    out=bytearray(); ring=bytearray([rinit]*rsize); r=rstart
    i=skip
    while i<len(comp) and len(out)<len(target)+64:
        flags=comp[i]; i+=1
        for bpos in range(8):
            bit=(flags>>(7-bpos))&1 if msbflag else (flags>>bpos)&1
            if i>=len(comp): break
            if (bit==1)==lit_is_1:
                c=comp[i]; i+=1
                out.append(c); ring[r]=c; r=(r+1)%rsize
            else:
                if i+1>=len(comp): break
                b1=comp[i]; b2=comp[i+1]; i+=2
                if pack=='cls': pos=b1|((b2&0xf0)<<4); ln=(b2&0x0f)+thr
                elif pack=='cls2': pos=b2|((b1&0xf0)<<4); ln=(b1&0x0f)+thr
                else: pos=b1|((b2>>4)<<8); ln=(b2&0x0f)+thr
                for k in range(ln):
                    c=ring[(pos+k)%rsize]; out.append(c); ring[r]=c; r=(r+1)%rsize
            if len(out)>=len(target)+64: break
    return bytes(out)

best=(0,None)
for skip in (0,2):
 for rsize in (4096,2048,1024):
  for rinit in (0,0x20):
   for rstart in (0, rsize-18, rsize-1):
    for lit1 in (True,False):
     for thr in (1,2,3):
      for pack in ('cls','cls2','alt'):
       for msbflag in (True,False):
        r=lzss_classic(comp,skip,rsize,rinit,rstart,lit1,thr,pack,msbflag)
        ml=matchlen(r)
        if ml>best[0]: best=(ml,(skip,rsize,rinit,rstart,lit1,thr,pack,msbflag,len(r)))
print('best',best[0],'of',len(target)); print(best[1])
