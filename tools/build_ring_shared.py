import struct, json, importlib.util
lang1=bytearray(open('jp/LANG1.BIN','rb').read())
HOOK=0x06074C30; CB=0x10D0; BUDGET=736   # 0x64C30..0x64F10 (live pointer at 0x64F10)
def dst_for_char(c): return 0x25E20000 | ((c*0x20 - 0x120) & 0x3FFFF)
spec=importlib.util.spec_from_file_location('wb','wordblob.py'); wb=importlib.util.module_from_spec(spec); spec.loader.exec_module(wb)
def tiles_of(word,nc):
    out=wb.render_word(word,nc,ink=1); return [out[i*32:i*32+32] for i in range(nc)],[out[(nc+i)*32:(nc+i)*32+32] for i in range(nc)]
LETTERS=['M','o','v','e','a','g','i','c','T','r','t','O','d']
alpha_top=[];alpha_bot=[]
for L in LETTERS:
    t,b=tiles_of(L,1); alpha_top.append(bytearray(t[0])); alpha_bot.append(bytearray(b[0]))
def setrow(tile,r,bits):
    for c in range(4): tile[r*4+c]=((0xF if bits[c*2] else 0)<<4)|(0xF if bits[c*2+1] else 0)
it=alpha_top[6]; setrow(it,2,[0,0,0,1,1,0,0,0]); setrow(it,3,[0,0,0,1,1,0,0,0]); setrow(it,4,[0]*8); alpha_top[6]=bytes(it)
atk_top,atk_bot=tiles_of('Attack',5)
tiles=[bytes(x) for x in alpha_top]+[bytes(x) for x in alpha_bot]+list(atk_top)+list(atk_bot)
assert len(tiles)==36
GAPS=[0x60130,0x601BC,0x60248,0x602D4,0x60378,0x60414,0x604A0,0x6052C,0x605B8]
for g in GAPS: assert all(b==0 for b in lang1[g:g+96]), hex(g)

# ---- ALIGNED 12-byte descriptors: [H top_off][H guard][B packed=(gdelta<<4)|bmode][B ncols][top6] ----
# All 16-bit fields at even offsets; fixed stride 12 (learned: mov.w/mov.l need alignment!)
MOVE=[0xC7,0xC8,0xC9,0xCA]; ATK=[0xE1,0xE2,0xE3,0xE4,0xE5]
MAG=[0xC7,0xCB,0xCC,0xCD,0xCE]; TRE=[0xCF,0xD0,0xCA,0xCB,0xD1]; ORD=[0xD2,0xD0,0xD3,0xCA,0xD0]
RING=[(0x28E,0x5CC,MOVE,0x0D),(0x40E,0x5D4,ATK,0x05),(0x58E,0x5D8,MAG,0x0D),
      (0x58E,0x5E8,TRE,0x0D),(0x70E,0x5E8,TRE,0x0D),(0x88E,0x5E8,TRE,0x0D),
      (0x28E,0x428,ORD,0x0D),(0x70E,0x428,ORD,0x0D),(0x88E,0x428,ORD,0x0D),(0xA0E,0x428,ORD,0x0D)]
# Sub-menu: write inside box interior (c10=top_off), guard at kanji cell (gdelta), bmode=0 (blank bottoms)
# Letter tile IDs at the REAL charbase (save-state vram stores VDP2 with +0x120 offset; old IDs were +9 off)
L={'F':0x04,'I':0x9E,'G':0x8F,'H':0x08,'T':0x02,'A':0x01,'R':0x29,'U':0x8B,'S':0x9A,'D':0x03,'M':0x05,'N':0x8D,'L':0x0A,'O':0x9F,'E':0x9C,'Y':0x99}
def w(s): return [L[c] for c in s]
PAL=4   # letter tiles use pixel value 14 -> need non-zero palette (stat-label palette); one nibble to change
# Words start AT the kanji cell; the cursor sits one cell LEFT and must never be touched.
# Words at c11 cover each kanji pair's full 4-cell span (c11-c14); guard = known kanji tile at c12 = top_off+2.
SUB=[(0x596,0x4F1,w('DUEL')),   # r11 c11; guard 0x4F1 at c12 (FRAY's Y tile is two-tone; DUEL uses clean tiles)
     (0x716,0x691,w('RUSH')),   # r14 c11; guard 0x691 at c12
     (0x896,0x611,w('HOLD')),   # r17 c11; guard 0x611 at c12
     (0xA16,0x619,w('USER'))]   # r20 c11; guard 0x619 at c12
DESCS=[(o,g,(0<<4)|bm,len(top),top) for o,g,top,bm in RING]+[(o,g,(PAL<<4)|0,len(tp),tp) for o,g,tp in SUB]
NIT=len(DESCS)
def pack(d):
    o,g,pk,nc,top=d; t=list(top)+[0]*(6-len(top)); assert pk<0x80 and nc<=6
    return struct.pack('>HHBB',o,g,pk,nc)+bytes(t)
rwtbl=b''.join(pack(d) for d in DESCS)
assert len(rwtbl)==NIT*12

DSTBASE=dst_for_char(CB); NDMA=12; SRCBASE=0x06070000
code=[]; I=lambda x: code.append(x&0xFFFF)
MLL={}; MLW={}
for r in (4,5,6,11,12,13,14): I(0x2F06|(r<<4))
I(0x4F22)
I(0xDE00); MLL[len(code)-1]='CPY'
# ---- GATE: (Move s1 AND Attack s2) OR (cursor s1 AND Order s1) ----
I(0x9000); MLW[len(code)-1]='MOFF'
I(0x6143); I(0x310C); I(0x6311)
I(0x9000); MLW[len(code)-1]='OGD'
I(0x3300); bf_try=len(code); I(0x8B00)
I(0x71FE)                       # add #-2,r1  (r1 = buf+0x28C, cursor cell)
I(0x6211)                       # r2 = @r1 (sign-ext harmless vs positive CURV)
I(0x9000); MLW[len(code)-1]='CURV'
I(0x3200); bt_dw=len(code); I(0x8900)
TRYMOVE=len(code)
I(0x9000); MLW[len(code)-1]='MGD'
I(0x3300); bf_g1=len(code); I(0x8B00)
I(0x9000); MLW[len(code)-1]='AOFF'
I(0x6143); I(0x310C); I(0x6211)
I(0x9000); MLW[len(code)-1]='AGD'
I(0x3200); bf_g2=len(code); I(0x8B00)
DOWRITE=len(code)
# ---- WRITE pass: fixed 12-byte stride, all word reads even-aligned ----
I(0xDD00); MLL[len(code)-1]='RWA'
I(0xEC00|NIT)
DESCLOOP=len(code)
I(0x60D5)                       # mov.w @r13+,r0   top_off
I(0x6143); I(0x310C)            # r1 = buf + top_off  (write ptr = guard ptr)
I(0x67D5)                       # mov.w @r13+,r7   guard
I(0x60D4)                       # mov.b @r13+,r0   packed (<0x80)
I(0x6503)                       # mov r0,r5        (r5 = packed, temp)
I(0x4009); I(0x4009)            # shlr2 x2         -> r0 = palette
I(0x6203); I(0x4201); I(0x321C) # r2 = r1 + (pal>>1)  [guard ptr: sub +2, ring +0]
I(0x4018); I(0x4008); I(0x4008) # shll8, shll2 x2  -> palette<<12
I(0x6B03)                       # mov r0,r11       (OR mask; 0 for ring items)
I(0x6053)                       # mov r5,r0        (packed)
I(0xC90F)                       # and #0x0F,r0     -> bmode
I(0x6503)                       # mov r0,r5
I(0x63D4)                       # mov.b @r13+,r3   ncols
I(0x66D3)                       # mov r13,r6       top[] ptr
I(0x7D06)                       # add #6,r13       fixed stride
I(0x6021)                       # mov.w @r2,r0     buf[guard]
I(0x3070)                       # cmp/eq r7,r0
bf_next2=len(code); I(0x8B00)   # bf NEXT (guard miss)
DOWR=len(code)
# truncate ring labels to 2 cells when sub-menu box open (c15 == BORD), ring items only (bmode!=0)
I(0x2558)                       # tst r5,r5
bt_setup=len(code); I(0x8900)   # bt SETUP (bmode==0: sub-menu item, no truncation)
I(0x9000); MLW[len(code)-1]='BORD'
I(0x6703)                       # mov r0,r7
I(0x8518)                       # mov.w @(8,r1),r0   [c7+8 = c15]
I(0x3070)                       # cmp/eq r7,r0
bf_setup=len(code); I(0x8B00)   # bf SETUP
I(0xE302)                       # mov #2,r3
SETUP=len(code)
I(0x6213); I(0x7240); I(0x7240) # r2 = r1 + 0x80 (bottom ptr)
I(0x6033)                       # mov r3,r0 (cell counter)
CELL=len(code)
I(0x6764); I(0x677C)            # mov.b @r6+,r7 ; extu.b (tops can be >=0x80)
I(0x27BB)                       # or r11,r7  (apply palette mask; 0 for ring)
I(0x2171); I(0x7102)            # write top ; r1+=2
I(0x6373); I(0x335C)            # r3 = r7 + bmode (ring bottoms; mask 0 there)
I(0x2558)                       # tst r5,r5
bf_nb=len(code); I(0x8B00)      # bf NB
I(0xE310); I(0x4318)            # r3 = 0x10<<8 = 0x1000 (opaque blank bottom)
NB=len(code)
I(0x2231); I(0x7202)            # write bottom ; r2+=2
I(0x4010); bf_cell=len(code); I(0x8B00)
NEXT=len(code)
I(0x4C10); bf_desc=len(code); I(0x8B00)
# ---- DMA: 16-bit src offsets + base reg; incremental dst; const count ----
I(0xDD00); MLL[len(code)-1]='DMA'
I(0xDB00); MLL[len(code)-1]='SRCB'
I(0xEC00|NDMA)
I(0xD500); MLL[len(code)-1]='DSTB'
I(0xE618)
DMAL=len(code)
I(0x64D5)                       # mov.w @r13+,r4 (offset <0x8000)
I(0x4E0B)                       # jsr @r14
I(0x34BC)                       # delay: add r11,r4  (completes src before copy_fn runs)
I(0x7560)                       # add #0x60,r5
I(0x4C10); bf_dma=len(code); I(0x8B00)
SKIPALL=len(code)
I(0x4F26)
for r in (14,13,12,11,6,5,4): I(0x60F6|(r<<8))
I(0xD000); MLL[len(code)-1]='CPY'
I(0x402B); I(0x0009)

def d8(f,t):
    d=t-f-2; assert -128<=d<=127,(f,t,d); return d&0xFF
code[bt_dw]=0x8900|d8(bt_dw,DOWRITE)
code[bt_setup]=0x8900|d8(bt_setup,SETUP)
for f,t in [(bf_try,TRYMOVE),(bf_g1,SKIPALL),(bf_g2,SKIPALL),(bf_next2,NEXT),(bf_setup,SETUP),(bf_nb,NB),(bf_cell,CELL),(bf_desc,DESCLOOP),(bf_dma,DMAL)]:
    code[f]=0x8B00|d8(f,t)

codebytes=b''.join(struct.pack('>H',x) for x in code)
litbase=(len(codebytes)+3)&~3
LONG=['CPY','RWA','DMA','SRCB','DSTB']; longoff={n:litbase+i*4 for i,n in enumerate(LONG)}
WORD=['MOFF','OGD','CURV','MGD','AOFF','AGD','BORD']; wordbase=litbase+len(LONG)*4; wordoff={n:wordbase+i*2 for i,n in enumerate(WORD)}
rwtbl_off=wordbase+len(WORD)*2
dmatbl_off=rwtbl_off+len(rwtbl)
assert (HOOK+dmatbl_off)&1==0
tailchunk_off=dmatbl_off+NDMA*2
tailchunk_off=(tailchunk_off+3)&~3
for idx,name in MLL.items():
    pc=idx*2; d=(longoff[name]-((pc+4)&~3))//4; assert 0<=d<=255,(name,d); code[idx]=(code[idx]&0xFF00)|d
for idx,name in MLW.items():
    pc=idx*2; d=(wordoff[name]-(pc+4))//2; assert 0<=d<=255,(name,d); code[idx]=(code[idx]&0xFF00)|d
codebytes=b''.join(struct.pack('>H',x) for x in code)
srcs=[0x06010000+g-SRCBASE for g in GAPS]+[HOOK+tailchunk_off+j*96-SRCBASE for j in range(3)]
assert all(0<s<0x8000 for s in srcs)
WV={'MOFF':0x028E,'OGD':0x0428,'CURV':0x306F,'MGD':0x05CC,'AOFF':0x040E,'AGD':0x05D4,'BORD':0x0314}
out=bytearray(codebytes); out+=b'\x00'*(litbase-len(codebytes))
out+=struct.pack('>IIIII',0x0604A26C,HOOK+rwtbl_off,HOOK+dmatbl_off,SRCBASE,DSTBASE)
for n in WORD: out+=struct.pack('>H',WV[n])
out+=rwtbl
for s in srcs: out+=struct.pack('>H',s)
out+=b'\x00'*(tailchunk_off-(dmatbl_off+NDMA*2))
for t in tiles[27:36]: out+=t
assert len(out)==tailchunk_off+9*32
assert len(out)<=BUDGET, 'over budget: %d'%len(out)
open('hook_shared.bin','wb').write(out)
gapwrites=[]; ci=0
for g in GAPS: gapwrites.append((g,b''.join(tiles[k] for k in range(ci,ci+3)).hex())); ci+=3
json.dump({'hook_len':len(out),'litbase':litbase,'rwtbl_off':rwtbl_off,'dmatbl_off':dmatbl_off,
           'tailchunk_off':tailchunk_off,'ndma':NDMA,'gapwrites':gapwrites,'dstbase':DSTBASE,'srcbase':SRCBASE,
           'ndesc':NIT},open('hook_shared_meta.json','w'))
print('hook_shared.bin %d bytes (budget %d, margin %d), %d desc (10 ring + 4 submenu), %d DMA (16-bit srcs)'%(len(out),BUDGET,BUDGET-len(out),NIT,NDMA))
