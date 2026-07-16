from diskio import read_file, RAW, HDR, USER, BIN
import struct
# Read PVD at LBA 16
pvd = read_file(16,2048)
root_rec = pvd[156:156+34]
root_lba = struct.unpack('<I', root_rec[2:6])[0]
root_len = struct.unpack('<I', root_rec[10:14])[0]
print('root dir lba',root_lba,'len',root_len)
def parse_dir(lba, length):
    data = read_file(lba, ((length+USER-1)//USER)*USER)
    entries=[]; i=0
    while i < length:
        rl = data[i]
        if rl==0:
            # advance to next sector boundary
            i = ((i//USER)+1)*USER
            if i>=length: break
            continue
        rec=data[i:i+rl]
        ext_lba=struct.unpack('<I',rec[2:6])[0]
        ext_len=struct.unpack('<I',rec[10:14])[0]
        flags=rec[25]
        namelen=rec[32]
        name=rec[33:33+namelen]
        entries.append((name,ext_lba,ext_len,flags))
        i+=rl
    return entries
for name,lba,length,flags in parse_dir(root_lba, root_len):
    try: nm=name.decode('ascii','replace')
    except: nm=str(name)
    print(f'{nm:24} lba={lba:8} size={length:10} flags={flags:#04x}')
