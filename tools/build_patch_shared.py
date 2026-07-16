import struct, shutil, cdecc, pyxdelta, hashlib, json
CLEAN='disc/Langrisser - Dramatic Edition (ja-JP)/LANGRISSER_DRAMATIC_EDITION.bin'
LANG1_LBA=202
hook=open('hook_shared.bin','rb').read()
meta=json.load(open('hook_shared_meta.json'))
gw=[(o,bytes.fromhex(d)) for o,d in meta['gapwrites']]
lang1=bytearray(open('jp/LANG1.BIN','rb').read())
assert struct.unpack('>I',lang1[0x2C0B8:0x2C0BC])[0]==0x0604A26C
lang1[0x2C0B8:0x2C0BC]=struct.pack('>I',0x06074C30)
assert all(b==0 for b in lang1[0x64C30:0x64C30+len(hook)]),'hook tail not free'
lang1[0x64C30:0x64C30+len(hook)]=hook
touched=[0x2C0B8,0x64C30,0x64C30+len(hook)-1]
for foff,data in gw:
    assert all(b==0 for b in lang1[foff:foff+len(data)]),'gap 0x%X not free'%foff
    lang1[foff:foff+len(data)]=data
    touched+=[foff,foff+len(data)-1]
shutil.copyfile(CLEAN,'out.bin')
f=open('out.bin','r+b')
sectors=sorted(set(o//2048 for o in touched))
print('changed file-sectors',sectors,'LBA',[LANG1_LBA+s for s in sectors])
for s in sectors:
    lba=LANG1_LBA+s; f.seek(lba*2352); sec=bytearray(f.read(2352))
    user=bytes(lang1[s*2048:s*2048+2048]); user=user+bytes(2048-len(user)) if len(user)<2048 else user
    sec[16:16+2048]=user; sec=cdecc.reframe(sec,lba); f.seek(lba*2352); f.write(sec)
f.close()
def extract(lba,size,binp):
    out=bytearray(); g=open(binp,'rb'); rem=size; sec=lba
    while rem>0: g.seek(sec*2352+16); out+=g.read(2048)[:min(2048,rem)]; rem-=min(2048,rem); sec+=1
    return bytes(out)
print('re-extract matches:', extract(202,len(lang1),'out.bin')==bytes(lang1))
OUT='/mnt/user-data/outputs/Langrisser1_EN_menu_ring_full.xdelta'
pyxdelta.run(CLEAN,'out.bin',OUT)
shutil.copyfile(CLEAN,'vc.bin'); pyxdelta.decode('vc.bin',OUT,'va.bin')
def md5(p):
    h=hashlib.md5(); g=open(p,'rb')
    for c in iter(lambda:g.read(1<<20),b''): h.update(c)
    return h.hexdigest()
print('round-trip ok:', md5('va.bin')==md5('out.bin'))
print('written',OUT)
