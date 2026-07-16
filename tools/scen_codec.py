import struct
def u32(d,o): return struct.unpack('>I',d[o:o+4])[0]
def p32(v): return struct.pack('>I',v)

def parse(data):
    n0=u32(data,0)//4
    tops=[u32(data,i*4) for i in range(n0)]
    # block starts = nonzero entries; last nonzero = EOF
    nz=[t for t in tops if t!=0]
    eof=nz[-1]; block_offs=nz[:-1]  # 21 block starts
    blocks=[]
    for bi,bstart in enumerate(block_offs):
        bend = block_offs[bi+1] if bi+1<len(block_offs) else eof
        bdata=data[bstart:bend]
        # section ptr table: first rel ptr / 4 = M
        M=u32(bdata,0)//4
        secptrs=[u32(bdata,i*4) for i in range(M)]
        sections=[]
        for si in range(M):
            s=secptrs[si]; e=secptrs[si+1] if si+1<M else len(bdata)
            sections.append(bdata[s:e])
        blocks.append({'start':bstart,'raw':bdata,'secptrs':secptrs,'sections':sections})
    return {'n0':n0,'tops':tops,'eof':eof,'blocks':blocks,'block_offs':block_offs}

def parse_section2(sec2):
    count=u32(sec2,0)//4
    offs=[u32(sec2,i*4) for i in range(count)]
    entries=[]
    for i in range(count):
        s=offs[i]; e=offs[i+1] if i+1<count else len(sec2)
        entries.append(sec2[s:e])
    return count,offs,entries

def build_section2(entries):
    count=len(entries)
    hdr_len=count*4
    out=bytearray()
    # offsets relative to sec2 start
    cur=hdr_len
    offs=[]
    for e in entries:
        offs.append(cur); cur+=len(e)
    for o in offs: out+=p32(o)
    for e in entries: out+=e
    return bytes(out)

def build_block(secptr_count, sections):
    # section ptr table (M u32 rel) + sections
    M=len(sections)
    hdr=M*4
    out=bytearray()
    cur=hdr
    ptrs=[]
    for s in sections:
        ptrs.append(cur); cur+=len(s)
    for p in ptrs: out+=p32(p)
    for s in sections: out+=s
    return bytes(out)

def serialize(model, pad=0x800):
    blocks=model['blocks']
    n0=model['n0']
    # rebuild each block bytes
    block_bytes=[build_block(len(b['sections']),b['sections']) for b in blocks]
    # lay out blocks padded to `pad`, after the top table (which is n0*4, itself padded to pad)
    top_table_len=n0*4
    first=((top_table_len+pad-1)//pad)*pad  # block0 start (0x800)
    starts=[]; cur=first
    for bb in block_bytes:
        starts.append(cur)
        cur+=((len(bb)+pad-1)//pad)*pad
    eof=cur
    # build top table
    tops=[0]*n0
    for i,s in enumerate(starts): tops[i]=s
    tops[len(starts)]=eof
    out=bytearray()
    for t in tops: out+=p32(t)
    # pad top table to first
    out+=b'\x00'*(first-len(out))
    # write blocks padded
    for i,bb in enumerate(block_bytes):
        assert len(out)==starts[i], (len(out),starts[i])
        out+=bb
        padlen=((len(bb)+pad-1)//pad)*pad - len(bb)
        out+=b'\x00'*padlen
    return bytes(out)

if __name__=='__main__':
    d=open('extracted/SCEN.DAT','rb').read()
    m=parse(d)
    print('blocks:',len(m['blocks']),'eof:',hex(m['eof']),'filelen:',hex(len(d)))
    out=serialize(m)
    print('round-trip len:',hex(len(out)),'==orig?',out==d)
    if out!=d:
        for i in range(min(len(out),len(d))):
            if out[i]!=d[i]:
                print('first diff @%05x: out=%02x orig=%02x'%(i,out[i],d[i])); break
        print('len out',len(out),'orig',len(d))
