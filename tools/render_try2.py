import struct
from PIL import Image
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
a0=d[offs[0]:offs[1]]

def render4bpp(data, cols=32, scale=4):
    tbytes=32; ntiles=max(1,len(data)//tbytes); rows=(ntiles+cols-1)//cols
    img=Image.new('L',(cols*8, rows*8),0); px=img.load()
    for t in range(ntiles):
        base=t*tbytes; tx=(t%cols)*8; ty=(t//cols)*8
        for i in range(tbytes):
            if base+i>=len(data): break
            b=data[base+i]; x=(i*2)%8; y=(i*2)//8
            px[tx+x,ty+y]=(b>>4)*17; 
            if x+1<8: px[tx+x+1,ty+y]=(b&0xf)*17
    return img.resize((img.width*scale,img.height*scale),Image.NEAREST)

# Hypothesis: skip 2-byte header, MSB bit-flag, 1=literal, 12/4 offset/len
def lzss_hdr(data, skip, msb, lit1, lenadd):
    out=bytearray(); i=skip; cur=0; nb=0
    def bit():
        nonlocal cur,nb,i
        if nb==0:
            cur=data[i]; i+=1; nb=8
        nb-=1
        return (cur>>nb)&1 if msb else (cur>>(7-nb))&1
    try:
        while i<len(data) or nb>0:
            if (bit()==1)==lit1:
                out.append(data[i]); i+=1
            else:
                hi=data[i]; lo=data[i+1]; i+=2
                off=hi|((lo&0xf0)<<4); ln=(lo&0xf)+lenadd
                for k in range(ln):
                    src=len(out)-off
                    out.append(out[src] if src>=0 else 0)
            if len(out)>50000: break
    except IndexError: pass
    return bytes(out)

# PCX-like RLE
def pcx_rle(data, skip):
    out=bytearray(); i=skip
    while i<len(data):
        b=data[i]; i+=1
        if (b&0xc0)==0xc0:
            cnt=b&0x3f
            if i<len(data):
                v=data[i]; i+=1; out.extend([v]*cnt)
        else:
            out.append(b)
    return bytes(out)

cands={
 'skip2_msb_lit1_a1':lambda:lzss_hdr(a0,2,True,True,1),
 'skip2_msb_lit0_a1':lambda:lzss_hdr(a0,2,True,False,1),
 'skip0_msb_lit1_a1':lambda:lzss_hdr(a0,0,True,True,1),
 'pcx_skip0':lambda:pcx_rle(a0,0),
 'pcx_skip2':lambda:pcx_rle(a0,2),
}
for n,f in cands.items():
    r=f(); print(n,len(r)); render4bpp(r).save(f'b_{n}.png')
