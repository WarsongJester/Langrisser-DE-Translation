import sh2emu, collections
m=sh2emu.Mem(); cpu=sh2emu.SH2(m)
trace=collections.deque(maxlen=60)
orig_exec=cpu.exec
def traced_exec(op):
    trace.append((( cpu.pc-2)&0xffffffff, op))
    return orig_exec(op)
cpu.exec=traced_exec
cpu.r[15]=0x0606FF00; cpu.r[14]=0x0606FF00
cpu.r[4]=0; cpu.r[5]=0x25E20000; cpu.r[6]=0xFFFFFFFF; cpu.r[7]=0x20200000
try:
    cpu.run(0x06011850, ret_to=0x00000001, max_ins=5000000)
    print('clean return')
except Exception as e:
    print('STOP:',e)
import capstone
md=capstone.Cs(capstone.CS_ARCH_SH, capstone.CS_MODE_SH2|capstone.CS_MODE_BIG_ENDIAN)
print('--- last 45 executed instructions ---')
for pc,op in list(trace)[-45:]:
    try:
        i=next(md.disasm(bytes([(op>>8)&0xff,op&0xff]),pc)); txt='%s %s'%(i.mnemonic,i.op_str)
    except StopIteration: txt='.word'
    print('  %08x: %04x  %s'%(pc,op,txt))
