import struct

class Mem:
    """Saturn address space backed by the dumps. Cache bits masked (phys = addr & 0x07FFFFFF)."""
    def __init__(self):
        self.low = bytearray(open('LOWWORK.BIN','rb').read())      # 0x00200000, 1MB
        self.hw  = bytearray(open('HIGHWORKRAM.BIN','rb').read())  # 0x06000000, 1MB
        self.vdp2 = bytearray(0x80000)                              # 0x05E00000, 512KB (output)
        self.vdp1 = bytearray(0x80000)                              # 0x05C00000
        self.io_log = []
    def _region(self, addr):
        a = addr & 0x07FFFFFF
        if 0x00200000 <= a < 0x00300000: return self.low,  a-0x00200000
        if 0x06000000 <= a < 0x06100000: return self.hw,   a-0x06000000
        if 0x05E00000 <= a < 0x05E80000: return self.vdp2, a-0x05E00000
        if 0x05C00000 <= a < 0x05C80000: return self.vdp1, a-0x05C00000
        return None, a
    def r8(self,a):
        buf,off=self._region(a)
        if buf is None: self.io_log.append(('r8',a)); return 0
        return buf[off]
    def r16(self,a):
        buf,off=self._region(a)
        if buf is None: self.io_log.append(('r16',a)); return 0
        return (buf[off]<<8)|buf[off+1]
    def r32(self,a):
        buf,off=self._region(a)
        if buf is None: self.io_log.append(('r32',a)); return 0
        return (buf[off]<<24)|(buf[off+1]<<16)|(buf[off+2]<<8)|buf[off+3]
    def w8(self,a,v):
        buf,off=self._region(a)
        if buf is None: self.io_log.append(('w8',a,v&0xff)); return
        buf[off]=v&0xff
    def w16(self,a,v):
        buf,off=self._region(a)
        if buf is None: self.io_log.append(('w16',a,v&0xffff)); return
        buf[off]=(v>>8)&0xff; buf[off+1]=v&0xff
    def w32(self,a,v):
        buf,off=self._region(a)
        if buf is None: self.io_log.append(('w32',a,v&0xffffffff)); return
        buf[off]=(v>>24)&0xff; buf[off+1]=(v>>16)&0xff; buf[off+2]=(v>>8)&0xff; buf[off+3]=v&0xff

def s8(v): v&=0xff; return v-0x100 if v&0x80 else v
def s16(v): v&=0xffff; return v-0x10000 if v&0x8000 else v
def s32(v): v&=0xffffffff; return v-0x100000000 if v&0x80000000 else v
def u32(v): return v&0xffffffff

class SH2:
    def __init__(self, mem):
        self.m=mem
        self.r=[0]*16
        self.pc=0; self.pr=0; self.gbr=0; self.vbr=0; self.mach=0; self.macl=0
        self.T=0
        self.cyc=0
        self.halt=False
    def reg(self,i): return self.r[i]&0xffffffff
    def setr(self,i,v): self.r[i]=v&0xffffffff
    def run(self, start, ret_to=0xDEADBEEF, max_ins=200000000):
        """Run from start; treat a return (PR popped) to ret_to as stop."""
        self.pc=start&0xffffffff
        self.pr=ret_to
        n=0
        while not self.halt:
            if self.pc==(ret_to&0xffffffff): return
            self.step()
            n+=1
            if n>max_ins:
                raise RuntimeError('max_ins exceeded at pc=%08x'%self.pc)
    def fetch(self,a): return self.m.r16(a)
    def step(self):
        op=self.fetch(self.pc)
        self.pc=(self.pc+2)&0xffffffff
        self.exec(op)
    def _branch_delay(self, target):
        # execute delay slot instruction at current pc, then jump
        op=self.fetch(self.pc); self.pc=(self.pc+2)&0xffffffff
        self.exec(op)
        self.pc=target&0xffffffff
    def exec(self,op):
        r=self.r
        n=(op>>8)&0xf; m=(op>>4)&0xf
        o=op>>12
        if o==0x6:
            t=op&0xf
            if t==0x0: r[n]=s8(self.m.r8(self.reg(m)))&0xffffffff; return # mov.b @Rm,Rn (sign)
            if t==0x1: r[n]=s16(self.m.r16(self.reg(m)))&0xffffffff; return # mov.w
            if t==0x2: r[n]=self.m.r32(self.reg(m)); return # mov.l
            if t==0x3: r[n]=self.reg(m); return # mov Rm,Rn
            if t==0x4: # mov.b @Rm+,Rn
                v=s8(self.m.r8(self.reg(m)))&0xffffffff
                if n!=m: r[m]=(self.reg(m)+1)&0xffffffff
                r[n]=v; return
            if t==0x5:
                r[n]=s16(self.m.r16(self.reg(m)))&0xffffffff
                if n!=m: r[m]=(self.reg(m)+2)&0xffffffff
                return
            if t==0x6:
                r[n]=self.m.r32(self.reg(m))
                if n!=m: r[m]=(self.reg(m)+4)&0xffffffff
                return
            if t==0x7: r[n]=(~self.reg(m))&0xffffffff; return # not
            if t==0x8: # swap.b
                v=self.reg(m); r[n]=((v&0xffff0000)|((v&0xff)<<8)|((v>>8)&0xff))&0xffffffff; return
            if t==0x9: # swap.w
                v=self.reg(m); r[n]=((v>>16)&0xffff)|((v&0xffff)<<16); return
            if t==0xa: # negc
                tmp=(0-self.reg(m)-self.T)&0xffffffff; r[n]=tmp; self.T=1 if (0-self.reg(m)-self.T)<0 else 0; return
            if t==0xb: r[n]=(-self.reg(m))&0xffffffff; return # neg
            if t==0xc: r[n]=self.reg(m)&0xff; return # extu.b
            if t==0xd: r[n]=self.reg(m)&0xffff; return # extu.w
            if t==0xe: r[n]=s8(self.reg(m))&0xffffffff; return # exts.b
            if t==0xf: r[n]=s16(self.reg(m))&0xffffffff; return # exts.w
        if o==0x2:
            t=op&0xf
            if t==0x0: self.m.w8(self.reg(n), self.reg(m)); return # mov.b Rm,@Rn
            if t==0x1: self.m.w16(self.reg(n), self.reg(m)); return
            if t==0x2: self.m.w32(self.reg(n), self.reg(m)); return
            if t==0x4: r[n]=(self.reg(n)-1)&0xffffffff; self.m.w8(self.reg(n), self.reg(m)); return # mov.b Rm,@-Rn
            if t==0x5: r[n]=(self.reg(n)-2)&0xffffffff; self.m.w16(self.reg(n), self.reg(m)); return
            if t==0x6: r[n]=(self.reg(n)-4)&0xffffffff; self.m.w32(self.reg(n), self.reg(m)); return
            if t==0x7: # div0s
                self.Q=(self.reg(n)>>31)&1; self.Mb=(self.reg(m)>>31)&1; self.T=self.Q^self.Mb; return
            if t==0x8: self.T=1 if (self.reg(n)&self.reg(m))==0 else 0; return # tst
            if t==0x9: r[n]=self.reg(n)&self.reg(m); return # and
            if t==0xa: r[n]=self.reg(n)^self.reg(m); return # xor
            if t==0xb: r[n]=self.reg(n)|self.reg(m); return # or
            if t==0xc: # cmp/str
                tmp=self.reg(n)^self.reg(m); self.T=1 if any(((tmp>>(8*i))&0xff)==0 for i in range(4)) else 0; return
            if t==0xd: r[n]=((self.reg(m)&0xffff)<<16)|(self.reg(n)&0xffff); return # xtrct? (approx)
            if t==0xe: # mulu.w
                self.macl=( (self.reg(n)&0xffff)*(self.reg(m)&0xffff) )&0xffffffff; return
            if t==0xf: # muls.w
                self.macl=( s16(self.reg(n))*s16(self.reg(m)) )&0xffffffff; return
        if o==0x3:
            t=op&0xf
            if t==0x0: self.T=1 if self.reg(n)==self.reg(m) else 0; return # cmp/eq
            if t==0x2: self.T=1 if self.reg(n)>=self.reg(m) else 0; return # cmp/hs (unsigned)
            if t==0x3: self.T=1 if s32(self.reg(n))>=s32(self.reg(m)) else 0; return # cmp/ge
            if t==0x4: # div1
                self._div1(n,m); return
            if t==0x5: # dmulu.l
                res=self.reg(n)*self.reg(m); self.mach=(res>>32)&0xffffffff; self.macl=res&0xffffffff; return
            if t==0x6: self.T=1 if self.reg(n)>self.reg(m) else 0; return # cmp/hi (unsigned)
            if t==0x7: self.T=1 if s32(self.reg(n))>s32(self.reg(m)) else 0; return # cmp/gt
            if t==0x8: r[n]=(self.reg(n)-self.reg(m))&0xffffffff; return # sub
            if t==0xa: # subc
                tmp=self.reg(n)-self.reg(m)-self.T; self.T=1 if tmp<0 else 0; r[n]=tmp&0xffffffff; return
            if t==0xb: # subv
                res=s32(self.reg(n))-s32(self.reg(m)); self.T=1 if res<-0x80000000 or res>0x7fffffff else 0; r[n]=res&0xffffffff; return
            if t==0xc: r[n]=(self.reg(n)+self.reg(m))&0xffffffff; return # add
            if t==0xd: # dmuls.l
                res=s32(self.reg(n))*s32(self.reg(m)); self.mach=(res>>32)&0xffffffff; self.macl=res&0xffffffff; return
            if t==0xe: # addc
                tmp=self.reg(n)+self.reg(m)+self.T; self.T=1 if tmp>0xffffffff else 0; r[n]=tmp&0xffffffff; return
            if t==0xf: # addv
                res=s32(self.reg(n))+s32(self.reg(m)); self.T=1 if res<-0x80000000 or res>0x7fffffff else 0; r[n]=res&0xffffffff; return
        if o==0xe: # mov #imm,Rn
            r[n]=s8(op&0xff)&0xffffffff; return
        if o==0x9: # mov.w @(disp,pc),Rn
            disp=op&0xff; addr=(self.pc+2+disp*2)&0xffffffff; r[n]=s16(self.m.r16(addr))&0xffffffff; return
        if o==0xd: # mov.l @(disp,pc),Rn
            disp=op&0xff; addr=(((self.pc+2)&0xfffffffc)+disp*4)&0xffffffff; r[n]=self.m.r32(addr); return
        if o==0xc:
            t=(op>>8)&0xf; d=op&0xff
            if t==0x0: self.m.w8(self.gbr+d, self.reg(0)); return
            if t==0x1: self.m.w16(self.gbr+d*2, self.reg(0)); return
            if t==0x2: self.m.w32(self.gbr+d*4, self.reg(0)); return
            if t==0x3: # trapa - stop
                self.halt=True; return
            if t==0x4: r[0]=s8(self.m.r8(self.gbr+d))&0xffffffff; return
            if t==0x5: r[0]=s16(self.m.r16(self.gbr+d*2))&0xffffffff; return
            if t==0x6: r[0]=self.m.r32(self.gbr+d*4); return
            if t==0x7: r[0]=(((self.pc+2)&0xfffffffc)+d*4)&0xffffffff; return # mova
            if t==0x8: self.T=1 if (self.reg(0)&d)==0 else 0; return # tst #imm,R0
            if t==0x9: r[0]=self.reg(0)&d; return # and #imm,R0
            if t==0xa: r[0]=self.reg(0)^d; return # xor
            if t==0xb: r[0]=self.reg(0)|d; return # or
            if t==0xd: # and.b #imm,@(R0,GBR)
                a=self.gbr+self.reg(0); self.m.w8(a, self.m.r8(a)&d); return
            if t==0xe: a=self.gbr+self.reg(0); self.m.w8(a, self.m.r8(a)^d); return
            if t==0xf: a=self.gbr+self.reg(0); self.m.w8(a, self.m.r8(a)|d); return
        if o==0x8:
            t=(op>>8)&0xf; d=op&0xff
            if t==0x0: self.m.w8(self.reg(m)+(op&0xf), self.reg(0)); return # mov.b R0,@(disp,Rm)  [m is (op>>4)&0xf]
            if t==0x1: self.m.w16(self.reg(m)+(op&0xf)*2, self.reg(0)); return
            if t==0x4: r[0]=s8(self.m.r8(self.reg(m)+(op&0xf)))&0xffffffff; return # mov.b @(disp,Rm),R0
            if t==0x5: r[0]=s16(self.m.r16(self.reg(m)+(op&0xf)*2))&0xffffffff; return
            if t==0x8: self.T=1 if self.reg(0)==s8(d) else 0; return # cmp/eq #imm,R0
            if t==0x9: # bt
                if self.T: self.pc=(self.pc+2+s8(d)*2)&0xffffffff
                return
            if t==0xb: # bf
                if not self.T: self.pc=(self.pc+2+s8(d)*2)&0xffffffff
                return
            if t==0xd: # bt/s
                if self.T: self._branch_delay((self.pc+2+s8(d)*2)&0xffffffff)
                return  # not taken: delay slot executes normally as next instr
            if t==0xf: # bf/s
                if not self.T: self._branch_delay((self.pc+2+s8(d)*2)&0xffffffff)
                return
        if o==0xa: # bra
            d=op&0xfff; d=d-0x1000 if d&0x800 else d
            self._branch_delay((self.pc+d*2)&0xffffffff); return
        if o==0xb: # bsr
            d=op&0xfff; d=d-0x1000 if d&0x800 else d
            self.pr=(self.pc+2)&0xffffffff
            self._branch_delay((self.pc+d*2)&0xffffffff); return
        if o==0x4:
            return self._exec4(op,n,m)
        if o==0x0:
            return self._exec0(op,n,m)
        if o==0x5: # mov.l @(disp,Rm),Rn
            r[n]=self.m.r32(self.reg(m)+(op&0xf)*4); return
        if o==0x1: # mov.l Rm,@(disp,Rn)
            self.m.w32(self.reg(n)+(op&0xf)*4, self.reg(m)); return
        if o==0x7: # add #imm,Rn
            r[n]=(self.reg(n)+s8(op&0xff))&0xffffffff; return
        raise RuntimeError('unhandled op %04x at pc=%08x'%(op,(self.pc-2)&0xffffffff))
    def _div1(self,n,m):
        # Simplified SH2 DIV1 step
        old_q=self.Q; self.Q=(self.reg(n)>>31)&1
        tmp=(self.reg(n)<<1)&0xffffffff; tmp|=self.T; 
        prev=self.reg(n)
        if old_q==self.Mb:
            r0=(tmp - self.reg(m))&0xffffffff; carry=1 if tmp< self.reg(m) else 0
        else:
            r0=(tmp + self.reg(m))&0xffffffff; carry=1 if (tmp+self.reg(m))>0xffffffff else 0
        self.r[n]=r0
        # (approximate; div not expected on hot path)
        self.Q=self.Q ^ self.Mb ^ carry
        self.T=1 if self.Q==self.Mb else 0
    def _exec4(self,op,n,m):
        r=self.r; t=op&0xff
        if t==0x00: # shll
            self.T=(self.reg(n)>>31)&1; r[n]=(self.reg(n)<<1)&0xffffffff; return
        if t==0x01: # shlr
            self.T=self.reg(n)&1; r[n]=self.reg(n)>>1; return
        if t==0x04: # rotl
            self.T=(self.reg(n)>>31)&1; r[n]=((self.reg(n)<<1)|self.T)&0xffffffff; return
        if t==0x05: # rotr
            self.T=self.reg(n)&1; r[n]=((self.reg(n)>>1)|(self.T<<31))&0xffffffff; return
        if t==0x24: # rotcl
            c=(self.reg(n)>>31)&1; r[n]=((self.reg(n)<<1)|self.T)&0xffffffff; self.T=c; return
        if t==0x25: # rotcr
            c=self.reg(n)&1; r[n]=((self.reg(n)>>1)|(self.T<<31))&0xffffffff; self.T=c; return
        if t==0x20: # shal
            self.T=(self.reg(n)>>31)&1; r[n]=(self.reg(n)<<1)&0xffffffff; return
        if t==0x21: # shar
            self.T=self.reg(n)&1; r[n]=(s32(self.reg(n))>>1)&0xffffffff; return
        if t==0x08: r[n]=(self.reg(n)<<2)&0xffffffff; return # shll2
        if t==0x09: r[n]=self.reg(n)>>2; return # shlr2
        if t==0x18: r[n]=(self.reg(n)<<8)&0xffffffff; return # shll8
        if t==0x19: r[n]=self.reg(n)>>8; return # shlr8
        if t==0x28: r[n]=(self.reg(n)<<16)&0xffffffff; return # shll16
        if t==0x29: r[n]=self.reg(n)>>16; return # shlr16
        if t==0x10: # dt
            r[n]=(self.reg(n)-1)&0xffffffff; self.T=1 if self.reg(n)==0 else 0; return
        if t==0x11: self.T=1 if s32(self.reg(n))>=0 else 0; return # cmp/pz
        if t==0x15: self.T=1 if s32(self.reg(n))>0 else 0; return # cmp/pl
        if t==0x0b: # jsr @Rn
            self.pr=(self.pc+2)&0xffffffff; tgt=self.reg(n); self._branch_delay(tgt); return
        if t==0x2b: # jmp @Rn
            tgt=self.reg(n); self._branch_delay(tgt); return
        if t==0x0e: self.sr_set(self.reg(n)); return # ldc Rn,SR
        if t==0x1e: self.gbr=self.reg(n); return # ldc Rn,GBR
        if t==0x2e: self.vbr=self.reg(n); return # ldc Rn,VBR
        if t==0x0a: self.mach=self.reg(n); return # lds Rn,MACH
        if t==0x1a: self.macl=self.reg(n); return # lds Rn,MACL
        if t==0x2a: self.pr=self.reg(n); return # lds Rn,PR
        if t==0x06: self.mach=self.m.r32(self.reg(n)); r[n]=(self.reg(n)+4)&0xffffffff; return # lds.l @Rn+,MACH
        if t==0x26: self.pr=self.m.r32(self.reg(n)); r[n]=(self.reg(n)+4)&0xffffffff; return # lds.l @Rn+,PR
        if t==0x22: self.m.w32((self.reg(n)-4)&0xffffffff,self.pr); r[n]=(self.reg(n)-4)&0xffffffff; return # sts.l PR,@-Rn
        if t==0x02: self.m.w32((self.reg(n)-4)&0xffffffff,self.mach); r[n]=(self.reg(n)-4)&0xffffffff; return # sts.l MACH,@-Rn
        if t==0x12: self.m.w32((self.reg(n)-4)&0xffffffff,self.macl); r[n]=(self.reg(n)-4)&0xffffffff; return # sts.l MACL,@-Rn
        if t==0x16: self.macl=self.m.r32(self.reg(n)); r[n]=(self.reg(n)+4)&0xffffffff; return # lds.l @Rn+,MACL
        if t==0x07: self.sr_set(self.m.r32(self.reg(n))); r[n]=(self.reg(n)+4)&0xffffffff; return # ldc.l @Rn+,SR
        if t==0x17: self.gbr=self.m.r32(self.reg(n)); r[n]=(self.reg(n)+4)&0xffffffff; return # ldc.l @Rn+,GBR
        if t==0x0f: # mac.w  @Rm+,@Rn+  (rare) - approximate skip
            self.r[m]=(self.reg(m)+2)&0xffffffff; self.r[n]=(self.reg(n)+2)&0xffffffff; return
        if t==0x4f: 
            self.r[m]=(self.reg(m)+4)&0xffffffff; self.r[n]=(self.reg(n)+4)&0xffffffff; return # mac.l (approx)
        if t==0x0d: # shld? no. 0x4nmd shld is 0x.... handled below
            pass
        # SHAD/SHLD use nibble m as reg
        sub=op&0xf
        if sub==0xc: # shad Rm,Rn
            sh=s32(self.reg(m))
            if sh>=0: r[n]=(self.reg(n)<<(sh&0x1f))&0xffffffff
            else:
                sh=-sh; r[n]=(s32(self.reg(n))>>(sh if sh<32 else 31))&0xffffffff
            return
        if sub==0xd: # shld Rm,Rn
            sh=s32(self.reg(m))
            if sh>=0: r[n]=(self.reg(n)<<(sh&0x1f))&0xffffffff
            else:
                sh=(-sh)&0x3f; r[n]=(self.reg(n)>>sh) if sh<32 else 0
            return
        if t==0x03: self.m.w32((self.reg(n)-4)&0xffffffff,self.sr_get()); r[n]=(self.reg(n)-4)&0xffffffff; return # stc.l SR,@-Rn
        if t==0x13: self.m.w32((self.reg(n)-4)&0xffffffff,self.gbr); r[n]=(self.reg(n)-4)&0xffffffff; return
        raise RuntimeError('unhandled 4-op %04x (t=%02x) at pc=%08x'%(op,t,(self.pc-2)&0xffffffff))
    def _exec0(self,op,n,m):
        r=self.r; t=op&0xf
        if t==0x3:
            sub=(op>>4)&0xf
            if sub==0x0: self.pr=(self.pc+2)&0xffffffff; self._branch_delay((self.pc+2+self.reg(n))&0xffffffff); return # bsrf
            if sub==0x2: self._branch_delay((self.pc+2+self.reg(n))&0xffffffff); return # braf
        if t==0x4: self.m.w8(self.reg(n)+self.reg(0), self.reg(m)); return # mov.b Rm,@(R0,Rn)
        if t==0x5: self.m.w16(self.reg(n)+self.reg(0), self.reg(m)); return
        if t==0x6: self.m.w32(self.reg(n)+self.reg(0), self.reg(m)); return
        if t==0x7: # mul.l
            self.macl=(self.reg(n)*self.reg(m))&0xffffffff; return
        if t==0x8:
            sub=(op>>4)&0xf
            if sub==0x0: self.T=0; return # clrt
            if sub==0x1: self.T=1; return # sett
            if sub==0x2: self.mach=0; self.macl=0; return # clrmac
        if t==0x9:
            sub=(op>>4)&0xf
            if sub==0x0: return # nop
            if sub==0x1: return # div0u
            if sub==0x2: r[n]=self.T; return # movt
        if t==0xa:
            sub=(op>>4)&0xf
            if sub==0x0: r[n]=self.mach; return # sts MACH,Rn
            if sub==0x1: r[n]=self.macl; return # sts MACL,Rn
            if sub==0x2: r[n]=self.pr; return # sts PR,Rn
        if t==0xb: # rts
            self._branch_delay(self.pr); return
        if t==0xc: r[n]=s8(self.m.r8(self.reg(0)+self.reg(m)))&0xffffffff; return # mov.b @(R0,Rm),Rn
        if t==0xd: r[n]=s16(self.m.r16(self.reg(0)+self.reg(m)))&0xffffffff; return
        if t==0xe: r[n]=self.m.r32(self.reg(0)+self.reg(m)); return
        if t==0x2:
            sub=(op>>4)&0xf
            if sub==0x0: r[n]=self.sr_get(); return # stc SR,Rn
            if sub==0x1: r[n]=self.gbr; return
            if sub==0x2: r[n]=self.vbr; return
        raise RuntimeError('unhandled 0-op %04x at pc=%08x'%(op,(self.pc-2)&0xffffffff))
    def sr_get(self): return self.T & 1
    def sr_set(self,v): self.T=v&1

print("sh2emu module ready")
