# Minimal MODE1/2352 reader for the LI data track
RAW=2352; HDR=16; USER=2048
BIN="disc/Langrisser - Dramatic Edition (ja-JP)/LANGRISSER_DRAMATIC_EDITION.bin"

def read_file(lba, size, binpath=BIN):
    out=bytearray()
    nsec=(size+USER-1)//USER
    with open(binpath,'rb') as f:
        for i in range(nsec):
            f.seek((lba+i)*RAW+HDR)
            out+=f.read(USER)
    return bytes(out[:size])

FILES={
 'LANG1.BIN':(202,413460),
 'FONT.DAT':(135070,220732),
 'SCEN.DAT':(136946,659456),
 '0.BIN':(142,121852),
}
if __name__=='__main__':
    import os
    os.makedirs('extracted',exist_ok=True)
    for name,(lba,sz) in FILES.items():
        d=read_file(lba,sz)
        open('extracted/'+name,'wb').write(d)
        print(name, lba, sz, len(d), d[:8].hex())
