import capstone
LANG1=open('extracted/LANG1.BIN','rb').read()
BASE=0x06010000
md=capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2 | capstone.CS_MODE_BIG_ENDIAN)
# disassemble whole file linearly, collect instructions
ins=[]
for i in md.disasm(LANG1, BASE):
    ins.append(i)
# index by address
print('total ins', len(ins))
# find windows containing both a 'shll/shlr/rotcl/rotl' and 'mov.b @rN+' within ~30 instr, and a backward branch (loop)
shifts={'shll','shlr','shll2','shlr2','rotcl','rotcr','rotl','rotr','shal','shar','shld'}
byterd=lambda s: ('mov.b' in s.mnemonic and '@r' in s.op_str and '+' in s.op_str)
cands=[]
for k in range(len(ins)):
    win=ins[k:k+40]
    has_shift=any(w.mnemonic in shifts for w in win)
    has_byterd=any(byterd(w) for w in win)
    has_bt=any(w.mnemonic in ('bt','bf','bt/s','bf/s','bra') and w.op_str and int(w.op_str,16)<=win[0].address for w in win if w.op_str.startswith('0x'))
    if has_shift and has_byterd and has_bt:
        cands.append(ins[k].address)
# dedupe nearby
ded=[]
for a in cands:
    if not ded or a-ded[-1]>0x40: ded.append(a)
print('candidate loop starts:', [hex(x) for x in ded[:40]])
