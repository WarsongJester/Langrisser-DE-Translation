import capstone
LANG1=open('extracted/LANG1.BIN','rb').read()
BASE=0x06010000
md=capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2 | capstone.CS_MODE_BIG_ENDIAN)
# decode each 2-byte aligned position independently (SH2 fixed 16-bit)
mnem=[None]*(len(LANG1)//2)
ops=[None]*(len(LANG1)//2)
for idx in range(len(LANG1)//2):
    off=idx*2
    g=md.disasm(LANG1[off:off+2],BASE+off)
    try:
        i=next(g); mnem[idx]=i.mnemonic; ops[idx]=i.op_str
    except StopIteration:
        mnem[idx]='?'; ops[idx]=''
shifts={'shll','shlr','shll2','shlr2','rotcl','rotcr','rotl','rotr','shal','shar','shld','shll8','shlr8','shll16','shlr16'}
def byterd(m,o): return m=='mov.b' and '@r' in o and ',r' in o and '+' in o
cands=[]
N=len(mnem)
for k in range(N-40):
    win=range(k,k+40)
    has_shift=any(mnem[j] in shifts for j in win)
    has_byterd=any(byterd(mnem[j],ops[j]) for j in win)
    # backward branch within window
    has_loop=False
    for j in win:
        if mnem[j] in ('bt','bf','bt/s','bf/s','bra') and ops[j].startswith('0x'):
            tgt=int(ops[j],16); addr=BASE+j*2
            if tgt<=addr and addr-tgt<0x60: has_loop=True
    if has_shift and has_byterd and has_loop:
        cands.append(BASE+k*2)
ded=[]
for a in cands:
    if not ded or a-ded[-1]>0x40: ded.append(a)
print('candidates:', [hex(x) for x in ded])
