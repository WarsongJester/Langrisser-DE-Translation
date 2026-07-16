#!/usr/bin/env python3
"""
langtool.py — Langrisser I (Sega Saturn, Dramatic Edition) script extract/insert tool.

Works directly on a MODE1/2352 .bin disc image (clean Japanese OR an English build).

Commands:
  extract  <game.bin> <script_dir>            pull the script out into editable .txt files
  insert   <game.bin> <script_dir> <out.bin>  re-encode edited .txt files into a new .bin
  check    <game.bin> <script_dir>            validate the script files without building

Text file format:
  ### 12            <- string header (index within the entry; do not renumber)
  Line one          <- {08} newlines between lines
  Line two
  <page>            <- {06}{07} box break, alone on a line
  Next box
  Control codes appear as tags: {05} {02} {03} {04:1C} {09:03} {0B} ... keep them as-is.
  Two ASCII spaces = one blank cell. Japanese text appears as literal kanji/kana.

Rendering model (Route B half-width packing):
  The engine draws one 16x16 cell per double-byte code. Two ASCII letters share one
  cell via composed pair glyphs stored in unused kanji slots of FONT.DAT. This tool
  reads existing pair glyphs out of the font (OCR against known letter shapes) and
  composes/allocates new ones automatically when your edits introduce new pairs.

Limits enforced on insert:
  dialogue (scenario NN dialogue/quiz): <=28 chars per line, <=3 lines per box
  names / item names / places:          <=16 chars  (hard engine buffer)
  item description lines:               <=32 chars  (hard engine buffer)
  SCEN.DAT total size:                  must fit the on-disc allocation
"""
import sys, os, json, struct, re, subprocess

RAW = 2352; HDR = 16; USER = 2048
S4 = 0x3EBC; S5 = 0x266FC; N4 = (62 - 16 + 1) * 94  # 4418 slots in S4
FONT_SIZE = 220732

# ---------------------------------------------------------------- ISO9660
def read_sector(f, lba):
    f.seek(lba * RAW + HDR); return f.read(USER)

def read_bytes(f, lba, size):
    out = bytearray()
    for i in range((size + USER - 1) // USER):
        out += read_sector(f, lba + i)
    return bytes(out[:size])

def iso_walk(f):
    files = {}
    pvd = read_sector(f, 16)
    if pvd[1:6] != b'CD001':
        raise SystemExit("Not a MODE1/2352 ISO9660 image (is this the raw .bin?)")
    root = pvd[156:156 + 34]
    rlba = struct.unpack('<I', root[2:6])[0]
    rsize = struct.unpack('<I', root[10:14])[0]
    def walkdir(lba, size, prefix):
        data = read_bytes(f, lba, size); off = 0
        while off < len(data):
            L = data[off]
            if L == 0:
                off = ((off // USER) + 1) * USER
                if off >= len(data): break
                continue
            rec = data[off:off + L]
            dlba = struct.unpack('<I', rec[2:6])[0]
            dsize = struct.unpack('<I', rec[10:14])[0]
            flags = rec[25]; nl = rec[32]
            name = rec[33:33 + nl].decode('ascii', 'replace').split(';')[0]
            if name not in ('\x00', '\x01'):
                p = prefix + name
                if flags & 2: walkdir(dlba, dsize, p + '/')
                else: files[p] = (dlba, dsize)
            off += L
    walkdir(rlba, rsize, '')
    return files

# ---------------------------------------------------------------- SCEN codec
def u32(d, o): return struct.unpack('>I', d[o:o + 4])[0]
def p32(v): return struct.pack('>I', v)

def scen_parse(data):
    n0 = u32(data, 0) // 4
    tops = [u32(data, i * 4) for i in range(n0)]
    nz = [t for t in tops if t != 0]
    eof = nz[-1]; block_offs = nz[:-1]
    blocks = []
    for bi, bstart in enumerate(block_offs):
        bend = block_offs[bi + 1] if bi + 1 < len(block_offs) else eof
        bdata = data[bstart:bend]
        M = u32(bdata, 0) // 4
        secptrs = [u32(bdata, i * 4) for i in range(M)]
        sections = []
        for si in range(M):
            s = secptrs[si]; e = secptrs[si + 1] if si + 1 < M else len(bdata)
            sections.append(bdata[s:e])
        # the block's 0x800 zero padding lands inside the last section; trim it
        # (serialize regenerates the padding, so unedited output is unchanged)
        if sections and sections[-1].endswith(b'\x00'):
            sections[-1] = sections[-1].rstrip(b'\x00') + b'\x00'
        blocks.append({'sections': sections})
    return {'n0': n0, 'blocks': blocks}

def scen_serialize(model, pad=0x800):
    def build_block(sections):
        M = len(sections); out = bytearray(); cur = M * 4; ptrs = []
        for s in sections: ptrs.append(cur); cur += len(s)
        for p in ptrs: out += p32(p)
        for s in sections: out += s
        return bytes(out)
    blocks = model['blocks']; n0 = model['n0']
    bb = [build_block(b['sections']) for b in blocks]
    first = ((n0 * 4 + pad - 1) // pad) * pad
    starts = []; cur = first
    for b in bb:
        starts.append(cur); cur += ((len(b) + pad - 1) // pad) * pad
    eof = cur
    tops = [0] * n0
    for i, s in enumerate(starts): tops[i] = s
    tops[len(starts)] = eof
    out = bytearray()
    for t in tops: out += p32(t)
    out += b'\x00' * (first - len(out))
    for i, b in enumerate(bb):
        out += b
        out += b'\x00' * (((len(b) + pad - 1) // pad) * pad - len(b))
    return bytes(out)

def sec2_parse(sec2):
    count = u32(sec2, 0) // 4
    offs = [u32(sec2, i * 4) for i in range(count)]
    entries = []
    for i in range(count):
        s = offs[i]; e = offs[i + 1] if i + 1 < count else len(sec2)
        entries.append(sec2[s:e])
    return entries

def sec2_build(entries):
    out = bytearray(); cur = len(entries) * 4; offs = []
    for e in entries: offs.append(cur); cur += len(e)
    for o in offs: out += p32(o)
    for e in entries: out += e
    return bytes(out)

# ---------------------------------------------------------------- kanji slot math
def kuten_to_sjis(ku, ten):
    j1 = (ku - 1) // 2
    s1 = j1 + (0x81 if j1 <= 0x1E else 0xC1)
    if ku % 2 == 1:
        s2 = ten + 0x3F
        if s2 >= 0x7F: s2 += 1
    else:
        s2 = ten + 0x9E
    return (s1 << 8) | s2

def sjis_to_slot(code):
    s1, s2 = code >> 8, code & 0xFF
    if not (0x81 <= s1 <= 0x9F or 0xE0 <= s1 <= 0xEF): return None
    j1 = s1 - 0x81 if s1 < 0xA0 else s1 - 0xC1
    ku = j1 * 2 + (1 if s2 >= 0x9F else 0) + 1
    ten = (s2 - 0x9E) if s2 >= 0x9F else (s2 - 0x40 if s2 >= 0x80 else s2 - 0x3F)
    if not (1 <= ten <= 94): return None
    if 16 <= ku <= 62: return (ku - 16) * 94 + (ten - 1)
    if 63 <= ku <= 83: return N4 + (ku - 63) * 94 + (ten - 1)
    return None

def slot_to_sjis(slot):
    if slot < N4: ku = 16 + slot // 94; ten = 1 + slot % 94
    else:
        s = slot - N4; ku = 63 + s // 94; ten = 1 + s % 94
    return kuten_to_sjis(ku, ten)

def slot_base(slot):
    return S4 + slot * 32 if slot < N4 else S5 + (slot - N4) * 32

TOTAL_SLOTS = N4 + 1978

# ---------------------------------------------------------------- letter glyphs
def load_letterglyphs():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'letterglyphs.json')
    d = json.load(open(p))
    return {ch: tuple(rows) for ch, rows in d.items()}

class Font:
    """FONT.DAT wrapper: OCR existing pair glyphs, compose/allocate new ones."""
    def __init__(self, data, glyphs):
        self.data = bytearray(data)
        self.glyphs = glyphs                       # char -> 16 row bytes
        self.rev = {g: c for c, g in glyphs.items()}
        self.pair2code = {}                        # (L,R) -> sjis code
        self.code2pair = {}
        for slot in range(TOTAL_SLOTS):
            base = slot_base(slot)
            right = tuple(self.data[base + r * 2] for r in range(16))
            left = tuple(self.data[base + r * 2 + 1] for r in range(16))
            L = self.rev.get(left); R = self.rev.get(right)
            if L is not None and R is not None:
                if L == ' ' and R == ' ':      # blank slot, not a real pair glyph
                    continue
                code = slot_to_sjis(slot)
                self.pair2code[(L, R)] = code
                self.code2pair[code] = (L, R)
        self.reserved = set()                      # slots we must not overwrite
        self.new_pairs = 0

    def reserve_code(self, code):
        slot = sjis_to_slot(code)
        if slot is not None: self.reserved.add(slot)

    def reserve_scan(self, blob):
        """Reserve every kanji slot referenced by SJIS sequences in a binary blob."""
        i = 0; n = len(blob)
        while i < n - 1:
            b = blob[i]
            if 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF:
                slot = sjis_to_slot((b << 8) | blob[i + 1])
                if slot is not None:
                    self.reserved.add(slot); i += 2; continue
            i += 1

    def finalize_reservations(self):
        for (L, R), code in self.pair2code.items():
            self.reserved.add(sjis_to_slot(code))
        self.free = [s for s in range(TOTAL_SLOTS - 1, -1, -1) if s not in self.reserved]

    def get_pair(self, L, R):
        key = (L, R)
        if key in self.pair2code: return self.pair2code[key]
        if L not in self.glyphs or R not in self.glyphs:
            raise KeyError(L if L not in self.glyphs else R)
        if not self.free:
            raise SystemExit("ERROR: out of free glyph slots (should never happen)")
        slot = self.free.pop(0)
        base = slot_base(slot)
        gL = self.glyphs[L]; gR = self.glyphs[R]
        for r in range(16):
            self.data[base + r * 2] = gR[r]        # right half
            self.data[base + r * 2 + 1] = gL[r]    # left half
        code = slot_to_sjis(slot)
        self.pair2code[key] = code; self.code2pair[code] = key
        self.new_pairs += 1
        return code

# ---------------------------------------------------------------- string decode
def decode_string(s, code2pair):
    """Game bytes -> editable text."""
    out = []; i = 0; n = len(s)
    while i < n:
        c = s[i]
        if c == 0x06 and i + 1 < n and s[i + 1] == 0x07:
            out.append('\n<page>\n'); i += 2
        elif c == 0x08:
            out.append('\n'); i += 1
        elif c in (0x04, 0x09) and i + 1 < n:
            out.append('{%02X:%02X}' % (c, s[i + 1])); i += 2
        elif c < 0x20:
            out.append('{%02X}' % c); i += 1
        elif 0x81 <= c <= 0x9F or 0xE0 <= c <= 0xEF:
            if i + 1 >= n:
                out.append('{%02X}' % c); i += 1; continue
            code = (c << 8) | s[i + 1]
            if code == 0x8140:
                out.append('  ')
            elif code in code2pair:
                out.append(''.join(code2pair[code]))
            else:
                try:
                    out.append(bytes([c, s[i + 1]]).decode('cp932'))
                except UnicodeDecodeError:
                    out.append('{%04X}' % code)
            i += 2
        elif 0x20 <= c <= 0x7E:
            out.append('{%02X}' % c); i += 1   # raw single-byte ASCII kept as tag (rare)
        else:
            try:
                out.append(bytes([c]).decode('cp932'))  # halfwidth kana
            except UnicodeDecodeError:
                out.append('{%02X}' % c)
            i += 1
    return ''.join(out)

# ---------------------------------------------------------------- string encode
TAG = re.compile(r'\{([0-9A-Fa-f]{2})\}|\{([0-9A-Fa-f]{2}):([0-9A-Fa-f]{2})\}|\{([0-9A-Fa-f]{4})\}')

def encode_line(text, font, where):
    """One display line of text (no {08}) -> bytes."""
    out = bytearray()
    pending = ''                                   # 0 or 1 buffered ASCII char
    def flush(pad=False):
        nonlocal pending
        if pending:
            if not pad:
                raise SystemExit(f"{where}: internal pairing error")
            out.extend(struct.pack('>H', font.get_pair(pending, ' ')))
            pending = ''
    i = 0; n = len(text)
    while i < n:
        m = TAG.match(text, i)
        if m:
            flush(pad=True)
            if m.group(1): out.append(int(m.group(1), 16))
            elif m.group(2): out += bytes([int(m.group(2), 16), int(m.group(3), 16)])
            else: out += struct.pack('>H', int(m.group(4), 16))
            i = m.end(); continue
        ch = text[i]
        if ch in font.glyphs:                      # ASCII-ish, half-width packable
            if pending:
                if pending == ' ' and ch == ' ':
                    out += b'\x81\x40'             # blank cell
                else:
                    try:
                        out += struct.pack('>H', font.get_pair(pending, ch))
                    except KeyError as e:
                        raise SystemExit(f"{where}: no glyph for character {e}")
                pending = ''
            else:
                pending = ch
            i += 1
        else:                                      # full-width / Japanese
            flush(pad=True)
            try:
                enc = ch.encode('cp932')
            except UnicodeEncodeError:
                raise SystemExit(f"{where}: cannot encode character {ch!r}")
            if len(enc) != 2:
                raise SystemExit(f"{where}: unsupported single-byte character {ch!r}")
            out += enc
            code = struct.unpack('>H', enc)[0]
            i += 1
    flush(pad=True)
    return bytes(out)

def encode_string(text, font, where):
    """Editable text (with newlines, <page>, tags) -> game bytes."""
    out = bytearray()
    pages = re.split(r'\n?<page>\n?', text)
    for pi, page in enumerate(pages):
        if pi > 0: out += b'\x06\x07'
        lines = page.split('\n')
        for li, line in enumerate(lines):
            if li > 0: out.append(0x08)
            out += encode_line(line, font, f"{where} page {pi+1} line {li+1}")
    return bytes(out)

def visible_len(text):
    """Length in half-width chars of a line, ignoring tags (tags count 0)."""
    t = TAG.sub('', text)
    return len(t)

# ---------------------------------------------------------------- file map
# (block, entry) -> (filename, kind)
def file_map():
    fm = {}
    fm[('g', 0)] = ('globals/0_menu.txt', 'menu')
    fm[('g', 1)] = ('globals/1_names.txt', 'name')
    fm[('g', 2)] = ('globals/2_items.txt', 'item')
    fm[('g', 3)] = ('globals/3_debug.txt', 'free')
    fm[('g', 4)] = ('globals/4_places.txt', 'free')
    fm[('g', 8)] = ('globals/8_scenario_titles.txt', 'menu')
    for s in range(1, 21):
        fm[(s - 1, 5)] = (f'scenarios/s{s:02d}_dialogue.txt', 'dialogue')
        fm[(s - 1, 6)] = (f'scenarios/s{s:02d}_winlose.txt', 'free')
        fm[(s - 1, 7)] = (f'scenarios/s{s:02d}_prologue.txt', 'free')
    fm[(20, 5)] = ('extra/quiz.txt', 'dialogue')
    fm[(20, 6)] = ('extra/battle_tutorial.txt', 'dialogue')
    fm[(20, 7)] = ('extra/b20_prologue.txt', 'free')
    return fm

HEADER_NOTE = {
 'dialogue': ("# Dialogue. A box is <=3 lines of <=28 characters. <page> starts a new box.\n"
              "# Two ASCII spaces = one blank cell. Keep {..} tags exactly as found.\n"),
 'name':     ("# One name per string, single line, <=16 characters (hard engine limit).\n"),
 'item':     ("# Strings 0-36 = item names (<=16 chars). 37+ = descriptions:\n"
              "# 3 strings per item (line1, line2, stat line), each <=32 chars, no <page>.\n"),
 'menu':     ("# UI strings. Keep lines short (<=16 chars is always safe). Keep tags as-is.\n"),
 'free':     ("# Keep the structure (tags, <page>, line breaks) close to the original.\n"),
}

# ---------------------------------------------------------------- extract
def get_li_files(f):
    files = iso_walk(f)
    need = {}
    for k in ('LANG1/SCEN.DAT', 'LANG1/FONT.DAT'):
        if k not in files: raise SystemExit(f"{k} not found in disc image")
        need[k] = files[k]
    for k in ('LANG1.BIN', '0.BIN'):
        need[k] = files.get(k)
    return need

def cmd_extract(binpath, outdir):
    glyphs = load_letterglyphs()
    with open(binpath, 'rb') as f:
        li = get_li_files(f)
        scen = read_bytes(f, *li['LANG1/SCEN.DAT'])
        fontd = read_bytes(f, *li['LANG1/FONT.DAT'])
    font = Font(fontd, glyphs)
    print(f"font: {len(font.pair2code)} existing letter-pair glyphs recognized")
    model = scen_parse(scen)
    fm = file_map()
    os.makedirs(outdir, exist_ok=True)
    for sub in ('globals', 'scenarios', 'extra'):
        os.makedirs(os.path.join(outdir, sub), exist_ok=True)
    written = 0
    for (loc, ei), (fname, kind) in sorted(fm.items(), key=lambda x: str(x[0])):
        bi = 0 if loc == 'g' else loc
        entries = sec2_parse(model['blocks'][bi]['sections'][2])
        if ei >= len(entries): continue
        strings = entries[ei].split(b'\x00')
        lines = [HEADER_NOTE[kind]]
        for si, sb in enumerate(strings):
            lines.append(f"### {si}\n")
            if sb:
                lines.append(decode_string(sb, font.code2pair) + "\n")
        with open(os.path.join(outdir, fname), 'w', encoding='utf-8') as fo:
            fo.write(''.join(lines))
        written += 1
    print(f"wrote {written} script files to {outdir}/")
    print("Edit the .txt files, then run:  python3 langtool.py insert <game.bin> "
          f"{outdir} <out.bin>")

# ---------------------------------------------------------------- parse script files
def parse_script_file(path):
    """Return list of (index, text) preserving order; text has no trailing newline."""
    strings = []
    cur = None; buf = []
    with open(path, encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if line.startswith('#') and not line.startswith('###'):
                continue
            m = re.match(r'###\s*(\d+)\s*$', line)
            if m:
                if cur is not None:
                    strings.append((cur, '\n'.join(buf)))
                cur = int(m.group(1)); buf = []
            elif cur is not None:
                buf.append(line)
    if cur is not None:
        strings.append((cur, '\n'.join(buf)))
    # strip trailing blank lines of each string (file formatting artifacts)
    out = []
    for idx, t in strings:
        while t.endswith('\n'): t = t[:-1]
        out.append((idx, t))
    return out

def validate(kind, idx, text, fname, problems):
    pages = re.split(r'\n?<page>\n?', text)
    for pi, page in enumerate(pages):
        lines = page.split('\n')
        if kind == 'dialogue':
            if len(lines) > 3:
                problems.append(f"{fname} ###{idx} box {pi+1}: {len(lines)} lines (max 3)")
            for li, line in enumerate(lines):
                vl = visible_len(line)
                if vl > 28:
                    problems.append(f"{fname} ###{idx} box {pi+1} line {li+1}: "
                                    f"{vl} chars (max 28): {line.strip()!r}")
        elif kind in ('name',):
            vl = visible_len(text)
            if vl > 16:
                problems.append(f"{fname} ###{idx}: {vl} chars (max 16): {text.strip()!r}")
        elif kind == 'item':
            for li, line in enumerate(lines):
                vl = visible_len(line)
                if vl > 32:
                    problems.append(f"{fname} ###{idx} line {li+1}: {vl} chars (max 32): "
                                    f"{line.strip()!r}")

# ---------------------------------------------------------------- insert
def cmd_insert(binpath, scriptdir, outpath=None, check_only=False):
    glyphs = load_letterglyphs()
    with open(binpath, 'rb') as f:
        li = get_li_files(f)
        scen_lba, scen_alloc = li['LANG1/SCEN.DAT']
        font_lba, _ = li['LANG1/FONT.DAT']
        scen = read_bytes(f, scen_lba, scen_alloc)
        fontd = read_bytes(f, font_lba, FONT_SIZE)
        lang1 = read_bytes(f, *li['LANG1.BIN']) if li['LANG1.BIN'] else b''
        bin0 = read_bytes(f, *li['0.BIN']) if li['0.BIN'] else b''
    font = Font(fontd, glyphs)
    model = scen_parse(scen)
    fm = file_map()

    # ---- read + validate all script files first
    edits = {}      # (loc, ei) -> list[(idx, text)]
    problems = []
    for (loc, ei), (fname, kind) in fm.items():
        path = os.path.join(scriptdir, fname)
        if not os.path.exists(path): continue
        strs = parse_script_file(path)
        for idx, text in strs:
            validate(kind, idx, text, fname, problems)
        edits[(loc, ei)] = strs
    if problems:
        print(f"FOUND {len(problems)} PROBLEM(S):")
        for p in problems: print("  " + p)
        raise SystemExit("Fix the problems above and retry.")
    if not edits:
        raise SystemExit(f"No script files found in {scriptdir}")
    print(f"parsed {len(edits)} script files, no limit violations")
    if check_only:
        print("check OK"); return

    # ---- reserve glyph slots: kanji still used by SCEN after edits, plus
    #      every kanji referenced by LANG1.BIN / 0.BIN (world map, class names)
    font.reserve_scan(lang1); font.reserve_scan(bin0)
    # kanji used in edited text (Japanese chars) + all untouched entries
    touched = set(edits.keys())
    for bi, b in enumerate(model['blocks']):
        entries = sec2_parse(b['sections'][2])
        for ei, e in enumerate(entries):
            key = ('g', ei) if ei in (0, 1, 2, 3, 4, 8) else (bi, ei)
            if key in touched: continue
            font.reserve_scan(e)
    for (loc, ei), strs in edits.items():
        for idx, text in strs:
            for ch in text:
                if ch not in font.glyphs and ord(ch) > 0x7F:
                    try:
                        enc = ch.encode('cp932')
                        if len(enc) == 2:
                            font.reserve_code(struct.unpack('>H', enc)[0])
                    except UnicodeEncodeError:
                        pass
    font.finalize_reservations()

    # ---- encode
    for bi, b in enumerate(model['blocks']):
        entries = sec2_parse(b['sections'][2])
        changed = False
        for ei in range(len(entries)):
            key = ('g', ei) if ei in (0, 1, 2, 3, 4, 8) else (bi, ei)
            if key not in edits: continue
            fname, kind = fm[key]
            old = entries[ei].split(b'\x00')
            new = list(old)
            for idx, text in edits[key]:
                if idx >= len(old):
                    raise SystemExit(f"{fname}: string ### {idx} does not exist "
                                     f"(entry has {len(old)} strings); do not add headers")
                new[idx] = encode_string(text, font, f"{fname} ###{idx}")
            entries[ei] = b'\x00'.join(new)
            changed = True
        if changed:
            b['sections'][2] = sec2_build(entries)

    new_scen = scen_serialize(model)
    print(f"SCEN.DAT: {len(new_scen)} bytes (allocation {scen_alloc}); "
          f"{font.new_pairs} new pair glyphs composed, "
          f"{len(font.pair2code)} total")
    if len(new_scen) > scen_alloc:
        raise SystemExit(f"ERROR: SCEN.DAT would be {len(new_scen)} bytes but only "
                         f"{scen_alloc} fit on disc. Shorten text by "
                         f"{len(new_scen)-scen_alloc} bytes.")
    new_scen = new_scen + b'\x00' * (scen_alloc - len(new_scen))

    # ---- splice into output image with EDC/ECC reframe
    import cdecc
    print("writing output image (this takes a minute)...")
    import shutil
    shutil.copyfile(binpath, outpath)
    with open(outpath, 'r+b') as f:
        def splice(lba, data):
            n = (len(data) + USER - 1) // USER
            for i in range(n):
                chunk = data[i * USER:(i + 1) * USER]
                if len(chunk) < USER: chunk = chunk + b'\x00' * (USER - len(chunk))
                f.seek((lba + i) * RAW)
                sec = bytearray(f.read(RAW))
                sec[HDR:HDR + USER] = chunk
                f.seek((lba + i) * RAW)
                f.write(cdecc.reframe(bytes(sec), lba + i))
        splice(font_lba, bytes(font.data))
        splice(scen_lba, new_scen)
    print(f"done: {outpath}")
    print("Tip: make an xdelta patch with\n"
          f"  xdelta3 -e -9 -f -s <CLEAN_JP.bin> {outpath} MyPatch.xdelta")

# ---------------------------------------------------------------- main
def main():
    a = sys.argv[1:]
    if not a or a[0] not in ('extract', 'insert', 'check'):
        print(__doc__); sys.exit(1)
    if a[0] == 'extract':
        if len(a) != 3: raise SystemExit("usage: langtool.py extract <game.bin> <script_dir>")
        cmd_extract(a[1], a[2])
    elif a[0] == 'insert':
        if len(a) != 4: raise SystemExit("usage: langtool.py insert <game.bin> <script_dir> <out.bin>")
        cmd_insert(a[1], a[2], a[3])
    elif a[0] == 'check':
        if len(a) != 3: raise SystemExit("usage: langtool.py check <game.bin> <script_dir>")
        cmd_insert(a[1], a[2], check_only=True)

if __name__ == '__main__':
    main()
