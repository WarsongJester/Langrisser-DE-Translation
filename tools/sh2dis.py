import capstone as C, struct
md=C.Cs(C.CS_ARCH_SH, C.CS_MODE_SH2|C.CS_MODE_BIG_ENDIAN)
md.detail=False
lang1=open('extracted/LANG1.BIN','rb').read()
BASE=0x06010000
def disasm(off,n=40):
    out=[]
    for ins in md.disasm(lang1[off:off+n*2], BASE+off):
        out.append((ins.address, ins.mnemonic, ins.op_str))
        if len(out)>=n: break
    return out
def show(off,n=40,label=''):
    print('--- %s @ file 0x%X (CPU 0x%X) ---'%(label,off,BASE+off))
    for a,m,o in disasm(off,n):
        print('  %08X  %s %s'%(a,m,o))
if __name__=='__main__':
    import sys
    show(int(sys.argv[1],16), int(sys.argv[2]) if len(sys.argv)>2 else 40, sys.argv[3] if len(sys.argv)>3 else '')
