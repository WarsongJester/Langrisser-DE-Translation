import build_conditions as bc, build_endings as be, scen_codec as sc, routeb as rb, cdecc, shutil, os

m=bc.model
ENDINGS_XLSX='/mnt/user-data/uploads/langendings.xlsx'
ep_blocks=be.parse_endings(ENDINGS_XLSX)
assert len(ep_blocks)==50, 'expected 50 epilogues, got %d'%len(ep_blocks)
ep_enc=[be.encode_epilogue(p) for p in ep_blocks]

applied=0; e4applied=0
for bi,b in enumerate(m['blocks']):
    cnt,offs,ents=sc.parse_section2(b['sections'][2])
    s6=ents[6].split(b'\x00')
    ents[6]=b'\x00'.join(bc.C(*bc.TR[s.decode('shift_jis','replace')]) if s.decode('shift_jis','replace') in bc.TR else s for s in s6)
    applied+=sum(1 for s in s6 if s.decode('shift_jis','replace') in bc.TR)
    s4=ents[4].split(b'\x00')
    ents[4]=b'\x00'.join(bc.C(*bc.E4TR[s.decode('shift_jis','replace')]) if s.decode('shift_jis','replace') in bc.E4TR else s for s in s4)
    e4applied+=sum(1 for s in s4 if s.decode('shift_jis','replace') in bc.E4TR)
    if bi==17:
        ents[9]=b'\x00'.join(ep_enc)
    b['sections'][2]=sc.build_section2(ents)

scen=sc.serialize(m)
nsec_scen=(len(scen)+2047)//2048
assert nsec_scen<=364, ('SCEN %d sect exceeds 364 alloc'%nsec_scen)
print('conditions:',applied,'  entry4 phrases:',e4applied,'  endings:',len(ep_enc))
print('SCEN', hex(len(scen)), '=', nsec_scen, 'sectors (budget 364)')
print('new glyphs:', len(bc.new_glyphs), '->', {sl:''.join(p) for sl,p in bc.new_glyphs.items()})
assert len(bc.new_glyphs)<=len(bc.free), 'ran out of blank slots'

font=bc.font
for slot,(L,R) in bc.new_glyphs.items():
    rb.compose_pair(font, rb.slot_base(slot), L, R)
assert len(font)==220732

d0=open('SCEN_en.DAT','rb').read(); m0=sc.parse(d0)
for bi in range(21):
    _,_,e_new=sc.parse_section2(m['blocks'][bi]['sections'][2])
    _,_,e_old=sc.parse_section2(m0['blocks'][bi]['sections'][2])
    assert len(e_new)==len(e_old), 'entry count changed block %d'%bi
    for ei in range(len(e_new)):
        if ei in (4,6): continue
        if bi==17 and ei==9: continue
        assert e_new[ei]==e_old[ei], ('regression block %d entry %d'%(bi,ei))
print('no regression outside entries 4/6 and block17 entry9')

SRC='Langrisser1_EN_43.bin'; OUT='Langrisser1_EN_45.bin'
shutil.copyfile(SRC,OUT)
f=open(OUT,'r+b')
def write_region(data,start_lba):
    nsec=(len(data)+2047)//2048
    for s in range(nsec):
        lba=start_lba+s
        f.seek(lba*2352); cur=bytearray(f.read(2352))
        chunk=data[s*2048:s*2048+2048]
        cur[16:16+len(chunk)]=chunk
        f.seek(lba*2352); f.write(cdecc.reframe(cur,lba))
    return nsec
nf=write_region(bytes(font),135070)
ns=write_region(scen,136946)
f.close()
print('spliced FONT %d sect, SCEN %d sect'%(nf,ns))
print('OUT size',os.path.getsize(OUT),'== base?',os.path.getsize(OUT)==os.path.getsize(SRC))
