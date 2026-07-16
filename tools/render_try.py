import struct
from lzcrack import assets, try_lzss
from PIL import Image

def render4bpp(data, tile_w=8, tile_h=8, cols=32, scale=4, label=''):
    # interpret as 4bpp linear tiles, 32 bytes/tile
    tbytes=tile_w*tile_h//2
    ntiles=max(1,len(data)//tbytes)
    rows=(ntiles+cols-1)//cols
    img=Image.new('L',(cols*tile_w, rows*tile_h),0)
    px=img.load()
    for t in range(ntiles):
        base=t*tbytes
        tx=(t%cols)*tile_w; ty=(t//cols)*tile_h
        for i in range(tbytes):
            if base+i>=len(data): break
            b=data[base+i]
            hi=(b>>4)&0xf; lo=b&0xf
            x=(i*2)%tile_w; y=(i*2)//tile_w
            px[tx+x,ty+y]=hi*17
            if x+1<tile_w: px[tx+x+1,ty+y]=lo*17
    img=img.resize((img.width*scale,img.height*scale),Image.NEAREST)
    return img

candidates={
 'msb_lit1_12_4_1':(True,True,12,4,1,4096,0x00,True),
 'msb_lit0_12_4_1':(True,False,12,4,1,4096,0x00,True),
 'lsb_lit1_12_4_1':(False,True,12,4,1,4096,0x00,True),
 'msb_lit1_12_4_3':(True,True,12,4,3,4096,0x00,True),
}
for name,cfg in candidates.items():
    r=try_lzss(assets[0],*cfg)
    print(name, 'len', len(r) if r else None)
    if r:
        render4bpp(r).save(f'a0_{name}.png')
