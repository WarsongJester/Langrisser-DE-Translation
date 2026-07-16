import freetype, struct
S1F=0xD9C; S4=0x3EBC; S5=0x266FC; END=0x35E3C
# ---- Toshiba 8x16 glyphs (ascent=13 matches the build) ----
_face=freetype.Face('MxPlus_ToshibaSat_8x16.ttf'); _face.set_pixel_sizes(0,16)
_cache={}
def glyph8(ch, ascent=13):
    if ch in _cache: return _cache[ch]
    _face.load_char(ch, freetype.FT_LOAD_RENDER|freetype.FT_LOAD_TARGET_MONO)
    b=_face.glyph.bitmap; rows=b.rows; w=b.width; pitch=b.pitch; buf=b.buffer
    top=_face.glyph.bitmap_top; left=max(0,_face.glyph.bitmap_left)
    out=[0]*16
    for ry in range(rows):
        rb=0
        for cx in range(min(w,8-left)):
            if (buf[ry*pitch+(cx>>3)]>>(7-(cx&7)))&1: rb|=(0x80>>(cx+left))
        d=ry+(ascent-top)
        if 0<=d<16: out[d]=rb
    out=tuple(out); _cache[ch]=out; return out
# ---- SJIS <-> kuten <-> slot ----
def kuten_to_sjis(ku,ten):
    j1=(ku-1)//2
    s1=j1+(0x81 if j1<=0x1E else 0xC1)
    if ku%2==1:
        s2=ten+0x3F
        if s2>=0x7F: s2+=1
    else:
        s2=ten+0x9E
    return s1,s2
def slot_to_sjis(slot):  # kanji slot index -> sjis bytes (S4 then S5)
    if slot< (62-16+1)*94:
        ku=16+slot//94; ten=1+slot%94
    else:
        s=slot-(62-16+1)*94; ku=63+s//94; ten=1+s%94
    return kuten_to_sjis(ku,ten)
def sjis_to_slot(s1,s2):
    j1=s1-0x81 if s1<0xA0 else s1-0xC1
    ku=j1*2+(1 if s2>=0x9F else 0)+1
    ten=(s2-0x9E) if s2>=0x9F else (s2-0x40 if s2>=0x80 else s2-0x3F)
    if 16<=ku<=62: return (ku-16)*94+(ten-1)
    if 63<=ku<=83: return (62-16+1)*94+(ku-63)*94+(ten-1)
    return None
def slot_base(slot):
    n4=(62-16+1)*94
    return S4+slot*32 if slot<n4 else S5+(slot-n4)*32
# ---- pair glyph compose/decode ----
def compose_pair(font, base, left_ch, right_ch):
    gA=glyph8(left_ch); gB=glyph8(right_ch)
    for r in range(16):
        font[base+r*2]=gB[r]; font[base+r*2+1]=gA[r]
# ---- OCR ----
CHARS=[chr(c) for c in range(0x20,0x7f)]
_rev={glyph8(c):c for c in CHARS}
def ocr_cell(font, base):
    gB=tuple(font[base+r*2] for r in range(16))
    gA=tuple(font[base+r*2+1] for r in range(16))
    L=_rev.get(gA); R=_rev.get(gB)
    return L,R
