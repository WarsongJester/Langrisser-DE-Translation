import sh2emu, struct
m=sh2emu.Mem()
cpu=sh2emu.SH2(m)
# stack in HWRAM, away from code/tables/work area
SP=0x0606FF00
cpu.r[15]=SP
cpu.r[14]=SP
# loader(r4=asset, r5=dest, r6=-1, r7=archive base)
cpu.r[4]=0           # font asset
cpu.r[5]=0x25E20000  # VDP2 VRAM dest (uncached)
cpu.r[6]=0xFFFFFFFF
cpu.r[7]=0x20200000
RET=0x00000001  # sentinel return addr (won't be code)
import sys
try:
    cpu.run(0x06011850, ret_to=RET, max_ins=5000000)
    print('returned cleanly, instr=%d'%0)
except Exception as e:
    print('STOP:', e)
# report VRAM font region
out=bytes(m.vdp2[0x20000:0x20040])
print('VRAM@0x20000:', out.hex())
nz=sum(1 for b in m.vdp2[0x20000:0x22000] if b)
print('nonzero in VRAM 0x20000..0x22000:', nz)
print('io accesses (first 12):', m.io_log[:12])
print('total io accesses:', len(m.io_log))
