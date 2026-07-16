# Route 1 glyph generator: render an English letter as a 24x24 menu glyph
# (3x3 tiles, 8x8 4bpp each), in the in-battle UI font's format.
from PIL import Image, ImageFont, ImageDraw
import struct

FONT_TTF='/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf'
ONPIX=0x0E  # palette index used by existing font ink

def render_letter(ch, px=23):
    # render into 24x24, vertically/horizontally centered, 1-bit
    f=ImageFont.truetype(FONT_TTF, px)
    im=Image.new('L',(24,24),0); d=ImageDraw.Draw(im)
    bb=d.textbbox((0,0),ch,font=f); w=bb[2]-bb[0]; h=bb[3]-bb[1]
    x=(24-w)//2-bb[0]; y=(24-h)//2-bb[1]
    d.text((x,y),ch,fill=255,font=f)
    return im.point(lambda v:1 if v>=128 else 0)

def to_tiles(im):
    # split 24x24 into 9 8x8 tiles (TL..BR row-major), each -> 32 bytes 4bpp
    tiles=[]
    for ty in range(3):
        for tx in range(3):
            b=bytearray(32)
            for r in range(8):
                for c in range(8):
                    on=im.getpixel((tx*8+c, ty*8+r))
                    if on:
                        bi=r*4+c//2
                        b[bi]|=(ONPIX<<4) if c%2==0 else ONPIX
            tiles.append(bytes(b))
    return tiles  # 9 tiles

def table_entry(tile_charnums):
    # 9 char numbers -> 18-byte glyph-table entry (big-endian halfwords)
    return b''.join(struct.pack('>H',cn&0xFFF) for cn in tile_charnums)

if __name__=='__main__':
    # preview: render the letters class-names/menus need, plus full alphabet
    missing='BFHJKLVWY'
    full='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    prev=Image.new('L',(len(full)*26,30),0)
    for i,ch in enumerate(full):
        g=render_letter(ch)
        prev.paste(g.point(lambda v:v*255),(i*26+1,3))
    prev=prev.resize((prev.width*2,prev.height*2),Image.NEAREST)
    prev.save('menuglyph_preview.png')
    # report tile cost (nonblank tiles per letter)
    import collections
    print('Tile cost per letter (nonblank 8x8 cells of the 3x3 block):')
    for ch in missing:
        t=to_tiles(render_letter(ch)); nb=sum(1 for x in t if any(x))
        print('  %s: %d/9 tiles'%(ch,nb))
    print('preview written: menuglyph_preview.png')
