import struct
v=open('VDP2VRAM.bin','rb').read()
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
comp=d[offs[0]:offs[1]]
target=v[0x20000:0x20000+0x2000]

def matchlen(r,t):
    m=0
    for a,b in zip(r,t):
        if a==b:m+=1
        else:break
    return m

def decode_word(comp,skip,litbit,rsize,rstart,relmode,split,thr,maxlen):
    out=bytearray(); ring=bytearray(rsize); r=rstart%rsize
    i=skip
    def rd16():
        nonlocal i
        w=(comp[i]<<8)|comp[i+1]; i+=2; return w
    try:
        while len(out)<maxlen and i<len(comp):
            ctrl=rd16()
            for b in range(16):
                bit=(ctrl>>(15-b))&1
                if i>=len(comp): break
                if bit==litbit:
                    c=comp[i]; i+=1
                    out.append(c); ring[r]=c; r=(r+1)%rsize
                else:
                    w=rd16()
                    if split=='12_4': o=w>>4; ln=(w&0xf)+thr
                    elif split=='4_12': ln=(w>>12)+thr; o=w&0xfff
                    elif split=='11_5': o=w>>5; ln=(w&0x1f)+thr
                    elif split=='5_11': ln=(w>>11)+thr; o=w&0x7ff
                    elif split=='13_3': o=w>>3; ln=(w&0x7)+thr
                    else: o=w>>4; ln=(w&0xf)+thr
                    pos=(r-o)%rsize if relmode else o%rsize
                    for k in range(ln):
                        c=ring[(pos+k)%rsize]; out.append(c); ring[r]=c; r=(r+1)%rsize
                if len(out)>=maxlen: break
    except IndexError: pass
    return bytes(out)

best=(0,None)
for skip in (0,2):
 for litbit in (0,1):
  for rsize in (4096,):
   for rstart in (0,rsize-18,4078):
    for relmode in (True,False):
     for split in ('12_4','4_12','11_5','5_11','13_3'):
      for thr in (1,2,3):
       r=decode_word(comp,skip,litbit,rsize,rstart,relmode,split,thr,len(target))
       ml=matchlen(r,target)
       if ml>best[0]: best=(ml,(skip,litbit,rstart,relmode,split,thr,len(r)))
print('best',best[0],'of',len(target)); print(best[1])
