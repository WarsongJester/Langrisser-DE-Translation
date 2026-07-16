import struct
v=open('VDP2VRAM.bin','rb').read()
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
comp=d[offs[0]:offs[1]]
target=v[0x20000:0x20000+0x1c00]

def decode(comp, msb, lit1, skip, match_decode, ring_init, lenadd, reltype):
    out=bytearray()
    i=skip; cur=0; nb=0
    def bit():
        nonlocal cur,nb,i
        if nb==0:
            if i>=len(comp): raise EOFError
            cur=comp[i]; i+=1; nb=8
        nb-=1
        return (cur>>nb)&1 if msb else (cur>>(7-nb))&1
    def byte():
        nonlocal i
        if i>=len(comp): raise EOFError
        b=comp[i]; i+=1; return b
    try:
        while len(out)<len(target)+64:
            if (bit()==1)==lit1:
                out.append(byte())
            else:
                b1=byte(); b2=byte()
                off,ln=match_decode(b1,b2)
                ln+=lenadd
                if reltype=='back':
                    start=len(out)-off
                    for k in range(ln):
                        out.append(out[start+k] if 0<=start+k<len(out) else ring_init)
                else: # absolute ring index window of 4096 zero-init
                    pass
            if i>=len(comp) and nb==0: break
    except EOFError: pass
    return bytes(out)

md_variants={
 'A_off12lo_len4': lambda b1,b2:( b1|((b2&0xf0)<<4), (b2&0x0f)),
 'B_off12_len4_swap': lambda b1,b2:( b2|((b1&0xf0)<<4), (b1&0x0f)),
 'C_len4hi_off12': lambda b1,b2:( ((b1&0x0f)<<8)|b2, (b1>>4)),
 'D_off8_len8': lambda b1,b2:( b1, b2),
 'E_len8_off8': lambda b1,b2:( b2, b1),
 'F_off12hi_len4': lambda b1,b2:( (b1<<4)|(b2>>4), (b2&0x0f)),
}
best=(0,None)
import itertools
for msb in (True,False):
 for lit1 in (True,False):
  for skip in (0,2):
   for mdname,md in md_variants.items():
    for lenadd in (1,2,3):
     r=decode(comp,msb,lit1,skip,md,0,lenadd,'back')
     # match length vs target
     ml=0
     for a,b in zip(r,target):
       if a==b: ml+=1
       else: break
     if ml>best[0]:
       best=(ml,(msb,lit1,skip,mdname,lenadd,len(r)))
print('best match prefix bytes:',best[0],'of',len(target))
print('config:',best[1])
