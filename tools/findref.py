import struct,sys
lang1=open('extracted/LANG1.BIN','rb').read()
BASE=0x06010000
def find_pcrel_loaders(target):
    # find mov.l @(disp,PC),Rn  (0xD?dd) or mov.w (0x9?dd) whose pointed constant == target
    hits=[]
    for off in range(0,len(lang1)-1,2):
        w=struct.unpack('>H',lang1[off:off+2])[0]
        op=w>>12
        if op==0xD: # mov.l @(disp,PC),Rn ; const at (PC&~3)+4+disp*4
            disp=w&0xFF; pc=BASE+off
            ca=((pc+4)&~3)+disp*4; coff=ca-BASE
            if 0<=coff<=len(lang1)-4:
                val=struct.unpack('>I',lang1[coff:coff+4])[0]
                if val==target: hits.append((off,(w>>8)&0xF))
    return hits
for name,t in [('VRAM font 0x25E20000',0x25E20000),('glyph table 0x060859F0',0x060859F0),
               ('VRAM base 0x25E00000',0x25E00000)]:
    h=find_pcrel_loaders(t)
    print('%-26s loaded by %d insns: %s'%(name,len(h),['file 0x%X(r%d)'%(o,r) for o,r in h[:10]]))
