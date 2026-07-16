import struct
v=open('VDP2VRAM.bin','rb').read()
d=open('extracted/IMG.DAT','rb').read()
offs=[struct.unpack('>I',d[i*4:i*4+4])[0] for i in range(207)]
comp=d[offs[0]:offs[1]]
target=v[0x20000:0x22000]

def bitarr(data):
    out=[]
    for byte in data:
        for k in range(8): out.append((byte>>(7-k))&1)
    return out
ba=bitarr(comp)
def rd(pos,n):
    val=0
    for k in range(n): val=(val<<1)|ba[pos+k]
    return val

def trace(offbits,lenbits,thr,verbose=True):
    pos=0; out=bytearray(); ops=0
    while pos+1<len(ba) and len(out)<len(target):
        f=ba[pos]; pos+=1
        if f==0:
            c=rd(pos,8); pos+=8
            exp=target[len(out)]
            out.append(c)
            tag = "OK" if c==exp else "<<MISMATCH"
            if verbose and ops<40: print("op%d bit~%d LIT %#04x exp %#04x %s"%(ops,pos,c,exp,tag))
            if c!=exp: return len(out)-1
        else:
            o=rd(pos,offbits); pos+=offbits
            l=rd(pos,lenbits); pos+=lenbits
            ln=l+thr
            st=len(out)-o; seg=[]
            for k in range(ln):
                c=out[st+k] if 0<=st+k<len(out) else 0
                out.append(c); seg.append(c)
            exp=target[len(out)-ln:len(out)]
            okk=bytes(seg)==bytes(exp)
            tag = "OK" if okk else "<<MM"
            if verbose and ops<40: print("op%d bit~%d MATCH off=%d len=%d -> %s exp %s %s"%(ops,pos,o,ln,bytes(seg).hex(),bytes(exp).hex(),tag))
            if not okk: return len(out)-ln
        ops+=1
    return len(out)

for cfg in [(12,4,2),(11,5,2),(12,4,3),(10,6,1),(13,3,2)]:
    print("=== offbits,lenbits,thr =",cfg,"===")
    ml=trace(*cfg, verbose=True)
    print("matched bytes:",ml); print()
