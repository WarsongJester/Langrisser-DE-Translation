# Translate in-battle Victory/Defeat conditions (SCEN.DAT entry 6) into Route B half-width,
# folding into the live English build (SCEN_en.DAT + FONT_en.DAT) without regression.
import routeb as rb, scen_codec as sc

jpfont=open('extracted/FONT.DAT','rb').read()
font=bytearray(open('FONT_en.DAT','rb').read())

# --- reconstruct existing pair<->code from build, and the build's changed slots ---
pair2code={}; build_changed=set()
o=rb.S4
while o+32<=len(font):
    if font[o:o+32]!=jpfont[o:o+32]:
        slot=(o-rb.S4)//32; build_changed.add(slot)
        L,R=rb.ocr_cell(font,o)
        if L and R: pair2code[(L,R)]=slot
    o+=32

# --- reserved real-JP kanji slots: any kanji code in still-Japanese SCEN content + LANG1 + 0.BIN ---
def is_kana(s1,s2):
    code=(s1<<8)|s2
    return 0x829f<=code<=0x82f1 or 0x8340<=code<=0x8396
reserved=set()
d=open('SCEN_en.DAT','rb').read(); model=sc.parse(d)
for b in model['blocks']:
    cnt,offs,ents=sc.parse_section2(b['sections'][2])
    for ei,blob in enumerate(ents):
        i=0
        while i+1<len(blob):
            s1,s2=blob[i],blob[i+1]
            if 0x81<=s1<=0x9f or 0xe0<=s1<=0xef:
                slot=rb.sjis_to_slot(s1,s2)
                if slot is not None and slot not in build_changed:
                    reserved.add(slot)   # a real kanji/kana the game still draws
                i+=2
            else: i+=1
for fn in ('extracted/LANG1.BIN','extracted/0.BIN'):
    dd=open(fn,'rb').read(); i=0
    while i+1<len(dd):
        s1,s2=dd[i],dd[i+1]
        if (0x88<=s1<=0x9f or 0xe0<=s1<=0xea):
            slot=rb.sjis_to_slot(s1,s2)
            if slot is not None: reserved.add(slot)
        i+=1

# --- free slot pool for NEW pairs ---
n4=(62-16+1)*94; ntot=n4+(83-63+1)*94
# Safest pool: slots that are BLANK (all-zero) in the original JP font -> repurposing harms nothing.
_jpf=jpfont
free=[s for s in range(ntot) if _jpf[rb.slot_base(s):rb.slot_base(s)+32]==b"\x00"*32 and s not in build_changed]
free_iter=iter(free)
new_glyphs={}  # slot -> (L,R)

def get_code_for_pair(L,R):
    if (L,R) in pair2code: return pair2code[(L,R)]
    slot=next(free_iter)
    pair2code[(L,R)]=slot; new_glyphs[slot]=(L,R)
    return slot

def enc_text_run(s):
    # pack 2 chars/cell -> bytes of sjis codes (or 0x8140 for "  ")
    out=bytearray()
    if len(s)%2: s=s+' '
    for k in range(0,len(s),2):
        L,R=s[k],s[k+1]
        if L==' ' and R==' ': out+=b'\x81\x40'; continue
        slot=get_code_for_pair(L,R); s1,s2=rb.slot_to_sjis(slot); out+=bytes([s1,s2])
    return bytes(out)

def encode_template(t):
    # t: list of tokens; str=ascii text run, ('raw',bytes)=control, '\u30fb'=bullet
    out=bytearray()
    for tok in t:
        if isinstance(tok,tuple): out+=tok[1]
        elif tok=='BULLET': out+=b'\x81\x45'
        else: out+=enc_text_run(tok)
    return bytes(out)

# convenience builders
def C(*parts): return encode_template(list(parts))
RAW=lambda *bs: ('raw',bytes(bs))
FMT=RAW(0x05); CONT=RAW(0x05,0x05); LORD=RAW(0x02)

# --- content-keyed translations: decoded-JP -> encoded-EN bytes ---
# keys are the DECODED japanese substring (with {NN} for control bytes)
def jp(*parts):  # build a JP key from decoded representation is unnecessary; we match raw bytes
    pass

# Map raw JP substring bytes -> English token list. We match by exact bytes.
def k(s): return s.encode('shift_jis')
TR = {}
def add(jpstr, *en): TR[jpstr]=list(en)
add('\x05・\x02の死亡', FMT,'BULLET',LORD,'dies')
add('\x05・レディンがナームと合流', FMT,'BULLET','Ledin joins Narm')
add('\x05・ナームの死亡', FMT,'BULLET','Narm dies')
add('\x05・クリスがマップ左上の', FMT,'BULLET','Chris escapes to the')
add('\x05\x05門へ脱出する', CONT,'gate at the top-left')
add('\x05・クリスの死亡', FMT,'BULLET','Chris dies')
add('\x05・シビリアンの全滅', FMT,'BULLET','All civilians die')
add('\x05・１６ターンの間レディンが', FMT,'BULLET','Ledin survives for')
add('\x05\x05生存する', CONT,'16 turns')
add('\x05・黒騎士ランスの撃破', FMT,'BULLET','Defeat Knight Lance')
add('\x05・占領軍司令ゼルドの撃破', FMT,'BULLET','Defeat Cmdr. Xeld')
add('\x05・ベルヌーイの撃破', FMT,'BULLET','Defeat Bernoulli')
add('\x05・アルバートの死亡', FMT,'BULLET','Albert dies')
add('\x05・ロード・ザルダフの撃破', FMT,'BULLET','Defeat Lord Zaldaff')
add('\x05・ロード・ザルダフの逃亡', FMT,'BULLET','Lord Zaldaff escapes')
add('\x05・レディンがマップ上の', FMT,'BULLET','Ledin reaches the')
add('\x05\x05街道の入り口に着く', CONT,'highway entrance')
add('\x05・キルヒナーの撃破', FMT,'BULLET','Defeat Kirchner')
add('\x05・レディンが最上階の階段に', FMT,'BULLET','Ledin reaches the stairs')
add('\x05\x05たどり着く', CONT,'on the top floor')
add('\x05・ディゴスの撃破', FMT,'BULLET','Defeat Digos')
add('\x05・ＮＰＣの全滅', FMT,'BULLET','All NPCs die')
add('\x05・ドラゴンの撃破', FMT,'BULLET','Defeat the Dragon')
add('\x05・ボーゼルを除く全ての', FMT,'BULLET','Defeat all foes')
add('\x05\x05敵の撃破', CONT,'except Bozel')
add('\x05・ナーギャの撃破', FMT,'BULLET','Defeat Nagya')
add('\x05・ニコリスの撃破', FMT,'BULLET','Defeat Nikoris')
add('\x05・全指揮官石化', FMT,'BULLET','All allies petrified')


# Entry-4 condition phrases referenced by {04}{XX} dictionary codes (global, all blocks).
E4TR={}
def adde4(jpstr,*en): E4TR[jpstr]=list(en)
adde4('\x05・ターンオーバー', FMT,'BULLET','Time runs out')
adde4('\x05・敵の全滅', FMT,'BULLET','Destroy all foes')
adde4('＊勝利条件', ('raw','＊'.encode('shift_jis')),'Victory Conditions')
adde4('＊敗北条件', ('raw','＊'.encode('shift_jis')),'Defeat Conditions')

if __name__=='__main__':
    # TEST on Scenario 1 entry 6: translate, then decode back.
    b0=model['blocks'][0]
    cnt,offs,ents=sc.parse_section2(b0['sections'][2])
    subs=ents[6].split(b'\x00')
    newsubs=[]
    for s in subs:
        dec=s.decode('shift_jis','replace')
        if dec in TR: newsubs.append(C(*TR[dec]))
        else: newsubs.append(s)
    # decode check
    code2pair={v:kk for kk,v in pair2code.items()}
    def show(bs):
        out=[];i=0
        while i<len(bs):
            x=bs[i]
            if x<0x20: out.append('{%02X}'%x); i+=1; continue
            s1,s2=bs[i],bs[i+1]
            if (s1,s2)==(0x81,0x40): out.append('_'); i+=2; continue
            if (s1,s2)==(0x81,0x45): out.append(chr(0x30fb)); i+=2; continue
            sl=rb.sjis_to_slot(s1,s2)
            if sl in code2pair: out.append(''.join(code2pair[sl])); i+=2; continue
            out.append('{%02x%02x}'%(s1,s2)); i+=2
        return ''.join(out)
    print('new pairs allocated so far:', len(new_glyphs))
    for i,s in enumerate(newsubs):
        print('%d| %s'%(i, show(s)))
