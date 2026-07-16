# Render a word into ncols 8x16 columns -> 2*ncols 8x8 4bpp tiles in static order
# (top row tiles left->right, then bottom row tiles left->right). ink index configurable.
import freetype, sys
face=freetype.Face('/mnt/user-data/uploads/MxPlus_ToshibaSat_8x16.ttf'); face.set_pixel_sizes(0,16)
def glyph(ch):
    face.load_char(ch, freetype.FT_LOAD_RENDER|freetype.FT_LOAD_TARGET_MONO)
    bm=face.glyph.bitmap; data=bm.buffer; pitch=bm.pitch; top=face.glyph.bitmap_top
    g=[[0]*8 for _ in range(16)]; y0=13-top
    for r in range(bm.rows):
        yy=y0+r
        if 0<=yy<16:
            b=data[r*pitch]
            for c in range(8):
                if b&(0x80>>c): g[yy][c]=1
    return g
def render_word(word, ncols, ink=1):
    W=ncols*8; canvas=[[0]*W for _ in range(16)]; n=len(word)
    if n*8<=W: spacing=8; x0=(W-n*8)//2
    else: spacing=(W-8)/(n-1); x0=0
    for i,ch in enumerate(word):
        g=glyph(ch); xo=int(round(x0+i*spacing))
        for r in range(16):
            for c in range(8):
                if g[r][c] and 0<=xo+c<W: canvas[r][xo+c]=ink
    # slice into tiles: top row (rows0-7) cols 0..ncols-1, then bottom row (rows8-15)
    def tile(col, rbase):
        out=bytearray()
        for r in range(rbase,rbase+8):
            for c in range(0,8,2):
                x=col*8
                hi=canvas[r][x+c]; lo=canvas[r][x+c+1]
                out.append((hi<<4)|lo)
        return bytes(out)
    blob=bytearray()
    for col in range(ncols): blob+=tile(col,0)   # top row
    for col in range(ncols): blob+=tile(col,8)   # bottom row
    return bytes(blob)
if __name__=='__main__':
    import struct
    word=sys.argv[1]; ncols=int(sys.argv[2]); out=sys.argv[3]
    b=render_word(word,ncols,1); open(out,'wb').write(b)
    print('%s: %d cols, %d tiles, %d bytes -> %s'%(word,ncols,ncols*2,len(b),out))
