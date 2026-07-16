# Content-keyed translator for SCEN.DAT entry 0 (UI/menu, global in all 21 blocks).
# Safe to run on any SCEN.DAT: it replaces specific JP substrings by content.
import scen_codec as sc

# Fullwidth SJIS encoder (Route A). Each ASCII char -> 2-byte fullwidth.
def sj(s):
    out=bytearray()
    for ch in s:
        c=ord(ch)
        if ch==' ': out+=b'\x81\x40'
        elif 0x21<=c<=0x7e:
            u=0xFEE0+c  # fullwidth
            out+=u.to_bytes(2,'big') if False else _fw(c)
        else:
            out+=ch.encode('shift_jis')
    return bytes(out)
def _fw(c):
    # map ascii printable to fullwidth SJIS via cp932
    fw=chr(0xFEE0+c)
    return fw.encode('shift_jis')

# Translation map: JP source substring -> English. Magic + summon names (clean, no control codes).
TMAP = {
 'マジックアロー':'Magic Arrow','ブラスト':'Blast','サンダー':'Thunder',
 'ファイアーボール':'Fireball','メテオ':'Meteor','ブリザード':'Blizzard',
 'トルネード':'Tornado','ターンアンデッド':'Turn Undead','アースクエイク':'Earthquake',
 'ヒール１':'Heal 1','ヒール２':'Heal 2','フォースヒール１':'Force Heal 1',
 'フォースヒール２':'Force Heal 2','スリープ':'Sleep','ミュート':'Mute',
 'プロテクション１':'Protect 1','プロテクション２':'Protect 2','アタック１':'Attack 1',
 'アタック２':'Attack 2','ゾーン':'Zone','テレポート':'Teleport','レジスト':'Resist',
 'チャーム':'Charm','クイック':'Quick','アゲイン':'Again','デクライン':'Decline','ストーン':'Stone',
 'ヴァルキリー':'Valkyrie','ホワイトドラゴン':'White Dragon','サラマンダー':'Salamander',
 'アイアンゴーレム':'Iron Golem','デーモンロード':'Demon Lord','スレイプニル':'Sleipnir','フェンリル':'Fenrir',
}

def translate_entry0_blob(e0):
    subs=e0.split(b'\x00')
    changed=0
    for i,s in enumerate(subs):
        try: txt=s.decode('shift_jis')
        except: continue
        if txt in TMAP:
            subs[i]=sj(TMAP[txt]); changed+=1
    return b'\x00'.join(subs), changed

def main():
    d=open('extracted/SCEN.DAT','rb').read()
    m=sc.parse(d)
    total=0
    for b in m['blocks']:
        count,offs,entries=sc.parse_section2(b['sections'][2])
        new_e0,ch=translate_entry0_blob(entries[0])
        entries[0]=new_e0
        b['sections'][2]=sc.build_section2(entries)
        total+=ch
    out=sc.serialize(m)
    open('SCEN_battle_en.dat','wb').write(out)
    print('translated substrings across all blocks:', total, '(expect 34 x 21 =', 34*21, ')')
    print('orig size', hex(len(d)), 'new size', hex(len(out)), 'grew', len(out)-len(d), 'bytes')
    # verify a sample
    m2=sc.parse(out)
    c,o,e=sc.parse_section2(m2['blocks'][0]['sections'][2])
    subs=e[0].split(b'\x00')
    print('sample re-read entry0[16]:', subs[16].decode('shift_jis','replace'))
    print('sample re-read entry0[43]:', subs[43].decode('shift_jis','replace'))
main()
