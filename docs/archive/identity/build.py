# Archived: generator for the UI-5 home mockups in this folder (dated record, nothing replaced it; the live tokens are apps/web/app/tokens.css).
import sys

FONTS = """
@font-face{font-family:'Geist Mono';font-weight:300;src:url(fonts/geist-mono-latin-300-normal.woff2)}
@font-face{font-family:'Geist Mono';font-weight:400;src:url(fonts/geist-mono-latin-400-normal.woff2)}
@font-face{font-family:'Geist Mono';font-weight:500;src:url(fonts/geist-mono-latin-500-normal.woff2)}
@font-face{font-family:'IBM Plex Mono';font-weight:300;src:url(fonts/ibm-plex-mono-latin-300-normal.woff2)}
@font-face{font-family:'Martian Mono';font-weight:300;src:url(fonts/martian-mono-latin-300-normal.woff2)}
@font-face{font-family:'DM Mono';font-weight:300;src:url(fonts/dm-mono-latin-300-normal.woff2)}
@font-face{font-family:'Sometype Mono';font-weight:400;src:url(fonts/sometype-mono-latin-400-normal.woff2)}
@font-face{font-family:'Inter';font-weight:400;src:url(fonts/inter-latin-400-normal.woff2)}
@font-face{font-family:'Inter';font-weight:500;src:url(fonts/inter-latin-500-normal.woff2)}
@font-face{font-family:'Inter';font-weight:600;src:url(fonts/inter-latin-600-normal.woff2)}
@font-face{font-family:'Noto Sans Devanagari';font-weight:300;src:url(fonts/noto-sans-devanagari-devanagari-300-normal.woff2);unicode-range:U+0900-097F,U+200C-200D,U+25CC}
@font-face{font-family:'Noto Sans Devanagari';font-weight:400;src:url(fonts/noto-sans-devanagari-devanagari-400-normal.woff2);unicode-range:U+0900-097F,U+200C-200D,U+25CC}
@font-face{font-family:'Noto Sans Devanagari';font-weight:500;src:url(fonts/noto-sans-devanagari-devanagari-500-normal.woff2);unicode-range:U+0900-097F,U+200C-200D,U+25CC}
"""

LIGHT = """
--bg-a:#E4ECFD;--bg-b:#C6D4F5;--bg-c:#D6E4FB;--orb1:#8FB6FF;--orb2:#B7A9FF;--orb3:#9CD3FF;
--fg:#0F1B4C;--mu:#2F3C78;--ac:#1D4FD8;--ac2:#4B5CE0;--acf:#FFFFFF;
--glass:rgba(255,255,255,.62);--glass-b:rgba(255,255,255,.75);--rule:rgba(15,27,76,.22);--ibd:#5A6AA8;
--chip:rgba(255,255,255,.55);--pill:rgba(15,27,76,.38);--ok:#0F6B4A;--okb:#DDF5EA;--am:#7A4B00;--amb:#FFF1CC;
--shadow:0 10px 30px rgba(40,60,140,.14);--glow:0 0 60px rgba(70,160,255,.55);
"""
DARK = """
--bg-a:#0B041A;--bg-b:#0B041A;--bg-c:#0B041A;--orb1:#2A1763;--orb2:#1B0F3A;--orb3:#251552;
--fg:#F4F1FF;--mu:#A39CB2;--ac:#6D5BD0;--ac2:#8B7CF6;--acf:#FFFFFF;
--glass:#120B24;--glass-b:#1B1530;--rule:rgba(255,255,255,.12);--ibd:#6F6890;
--chip:#201B3E;--pill:rgba(255,255,255,.35);--ok:#56C59D;--okb:#10241f;--am:#F5B942;--amb:#2e2410;
--shadow:none;--glow:0 0 60px rgba(124,108,240,.55);
"""

CSS = """
*{box-sizing:border-box;margin:0}
html,body{width:100%;height:100%}
body{font-family:'Inter','Noto Sans Devanagari',system-ui,sans-serif;color:var(--fg)}
.app{position:relative;overflow:hidden;min-height:100vh;
 background:linear-gradient(135deg,var(--bg-a) 0%,var(--bg-b) 48%,var(--bg-c) 100%)}
.dark .app{background:radial-gradient(900px 420px at 50% -10%,#1d0f40 0%,transparent 70%),#0B041A}
.orb{position:absolute;border-radius:50%;filter:blur(70px);opacity:.75;pointer-events:none}
.o1{width:520px;height:520px;background:var(--orb1);left:-120px;top:240px}
.o2{width:480px;height:480px;background:var(--orb2);right:-100px;top:-120px}
.o3{width:420px;height:420px;background:var(--orb3);right:160px;bottom:-220px}
.dark .orb{opacity:.35}
.mono{font-family:'Geist Mono','Noto Sans Devanagari',ui-monospace,monospace;text-transform:uppercase;letter-spacing:.06em}
.wrap{position:relative;z-index:2;max-width:1280px;margin:0 auto;padding:0 56px}
.top{display:flex;align-items:center;justify-content:space-between;padding:26px 0}
.logo{display:flex;align-items:center;gap:10px;font-size:13px;font-weight:400}
.ring{width:22px;height:22px;border-radius:50%;border:2px solid var(--fg);opacity:.85;position:relative}
.ring:after{content:'';position:absolute;inset:3px;border-radius:50%;border:1.5px solid var(--ac2);opacity:.9}
.nav{display:flex;gap:30px;padding:12px 30px;border-radius:999px;background:var(--glass-b);backdrop-filter:blur(14px);font-size:12px;box-shadow:var(--shadow)}
.dark .nav{border:1px solid var(--rule)}
.right{display:flex;align-items:center;gap:14px;font-size:12px}
.seg{display:flex;gap:2px;padding:3px;border-radius:12px;background:var(--glass);border:1px solid var(--rule);backdrop-filter:blur(10px)}
.seg i{width:32px;height:28px;border-radius:9px;display:flex;align-items:center;justify-content:center;color:var(--mu)}
.seg i.on{background:var(--chip);color:var(--fg)}
.seg svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.tags{display:flex;gap:10px;justify-content:center;margin:26px 0 22px}
.pill{border:1px solid var(--pill);border-radius:999px;padding:6px 14px;font-size:11.5px}
.rule{height:1px;background:var(--rule);width:100%}
.display{font-family:'Geist Mono','Noto Sans Devanagari',ui-monospace,monospace;font-weight:300;text-transform:uppercase;letter-spacing:-.03em;line-height:1.02;color:var(--fg)}
.hero{padding:30px 0;text-align:left}
.hero .display{font-size:84px}
.inline{display:inline-flex;align-items:center;justify-content:center;vertical-align:middle;margin:0 8px;padding:0 34px;height:78px;border-radius:999px;
 background:linear-gradient(90deg,#4DB4FF,#7AA2F7);color:#0F1B4C;font-size:15px;letter-spacing:.1em;font-weight:500;box-shadow:var(--glow)}
.dark .inline{background:linear-gradient(90deg,#6D5BD0,#5B4CC8);color:#fff}
.sub{display:grid;grid-template-columns:1fr 1fr;gap:28px;margin-top:26px;align-items:start}
.cmp{background:var(--glass);border:1px solid var(--glass-b);backdrop-filter:blur(14px);border-radius:22px;padding:14px 14px 12px 20px;box-shadow:var(--shadow)}
.dark .cmp{border-color:var(--rule)}
.cmp .ph{font-size:16px;color:var(--mu);padding:4px 0 14px}
.cr{display:flex;justify-content:space-between;align-items:center}
.md{display:flex;gap:4px;padding:3px;border-radius:999px;background:var(--chip)}
.md span{padding:6px 14px;border-radius:999px;font-size:11.5px;color:var(--mu)}
.md span.on{background:var(--ac);color:var(--acf)}
.send{width:44px;height:44px;border-radius:50%;background:var(--ac);display:flex;align-items:center;justify-content:center}
.send svg{width:20px;height:20px;stroke:#fff;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:22px}
.card{background:var(--glass);border:1px solid var(--glass-b);backdrop-filter:blur(14px);border-radius:18px;padding:16px;box-shadow:var(--shadow)}
.dark .card{border-color:var(--rule)}
.card .t{font-size:12.5px;margin:12px 0 6px}
.card .d{font-size:14px;color:var(--mu);line-height:1.4}
.ico{width:36px;height:36px;border-radius:11px;background:var(--chip);display:flex;align-items:center;justify-content:center;color:var(--ac)}
.dark .ico{color:var(--ac2)}
.ico svg{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.tag{display:inline-block;margin-top:10px;padding:2px 10px;border-radius:999px;font-size:11px}
.tag.ok{background:var(--okb);color:var(--ok)}.tag.am{background:var(--amb);color:var(--am)}.tag.ac{background:var(--chip);color:var(--ac)}.dark .tag.ac{color:#C9C2FF}
.about{font-size:12.5px;line-height:1.7;max-width:360px;color:var(--fg)}
.about b{display:block;font-weight:400;opacity:.7;margin-bottom:6px}
.prog{display:flex;align-items:center;gap:16px;background:var(--glass);border:1px solid var(--glass-b);border-radius:18px;padding:14px 16px;backdrop-filter:blur(14px);box-shadow:var(--shadow)}
.dark .prog{border-color:var(--rule)}
.sphere{width:68px;height:68px;border-radius:50%;flex:none;display:flex;align-items:center;justify-content:center;color:#fff;font-size:15px;font-weight:500;
 background:radial-gradient(circle at 32% 28%,#9fd8ff 0%,#2d8cf0 45%,#0a4bb8 100%);box-shadow:0 0 28px rgba(45,140,240,.55)}
.dark .sphere{background:radial-gradient(circle at 32% 28%,#c9c2ff 0%,#7C6CF0 45%,#3b2f9a 100%);box-shadow:0 0 28px rgba(124,108,240,.55)}
.foot{display:flex;justify-content:space-between;align-items:center;padding:22px 0 30px;font-size:12px;color:var(--mu)}
/* phone */
.phone .wrap{padding:0 18px;max-width:none}
.phone .top{padding:16px 0}
.phone .nav{display:none}
.phone .hero{padding:18px 0}
.phone .hero .display{font-size:40px}
.phone .inline{height:42px;padding:0 16px;font-size:11px;margin:4px 4px}
.phone .sub{grid-template-columns:1fr;gap:16px}
.phone .cards{grid-template-columns:1fr;gap:10px}
.phone .tags{margin:8px 0 14px}
.phone .about{display:none}
.phone .seg{padding:2px}
.phone .foot{display:none}
"""

SUN = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
MOON = '<svg viewBox="0 0 24 24"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
MON = '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>'
BOLT = '<svg viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>'
REF = '<svg viewBox="0 0 24 24"><path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/></svg>'
TGT = '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/></svg>'
ARROW = '<svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg>'


def page(theme, phone=False, lang="en"):
    head = {
        "en": ("WHAT SHALL WE LEARN", "TODAY?"),
        "hi": ("आज हम क्या सीखें", "आज?"),
    }[lang]
    root = ("dark" if theme == "dark" else "light") + (" phone" if phone else "")
    on_light = theme == "light"
    return f"""<!doctype html><html class="{root}"><head><meta charset="utf-8"><style>{FONTS}
.light{{{LIGHT}}} .dark{{{DARK}}} {CSS}</style></head><body>
<div class="app {root}">
 <div class="orb o1"></div><div class="orb o2"></div><div class="orb o3"></div>
 <div class="wrap">
  <div class="top">
   <div class="logo mono"><span class="ring"></span>YourTutor</div>
   <div class="nav mono"><span>Learn</span><span>Practise</span><span>Revise</span><span>My notes</span></div>
   <div class="right mono"><span>Log in</span><div class="seg"><i class="{'' if on_light else ''}">{MON}</i><i class="{'on' if on_light else ''}">{SUN}</i><i class="{'' if on_light else 'on'}">{MOON}</i></div></div>
  </div>
  <div class="tags mono"><span class="pill">Class 10 to 12</span><span class="pill">Adaptive</span></div>
  <div class="rule"></div>
  <div class="hero">
   <div class="display">{head[0]}</div>
   <div class="display"><span class="inline mono">{'Try one question' if lang=='en' else 'एक सवाल हल करें'}</span>{head[1]}</div>
  </div>
  <div class="rule"></div>
  <div class="sub">
   <div>
    <div class="cmp"><div class="ph">Find a topic or ask about your syllabus</div>
     <div class="cr"><div class="md mono"><span class="on">Learn</span><span>Practise</span><span>Revise</span></div><div class="send">{ARROW}</div></div></div>
    <div class="cards">
     <div class="card"><div class="ico">{BOLT}</div><div class="t mono">Continue Integrals</div><div class="d">3 of 8 skills, about 15 minutes.</div><span class="tag ac">In progress</span></div>
     <div class="card"><div class="ico">{REF}</div><div class="t mono">Review due</div><div class="d">3 cards, 5 quick minutes.</div><span class="tag am">Due today</span></div>
     <div class="card"><div class="ico">{TGT}</div><div class="t mono">Worth your time</div><div class="d">Differential equations.</div><span class="tag ok">High weight</span></div>
    </div>
   </div>
   <div>
    <div class="about mono"><b>About</b>Adaptive learning that evolves with your progress and your syllabus.</div>
    <div class="prog" style="margin-top:22px"><div class="sphere">38%</div><div><div class="mono" style="font-size:12px;margin-bottom:6px">Syllabus covered</div><div style="font-size:14px;color:var(--mu);line-height:1.4">Today: about 25 minutes. Review 3 cards, then practise Integrals.</div></div></div>
   </div>
  </div>
  <div class="foot mono"><span>No account needed. Progress stays on this device.</span><span>★ 5.0 example rating</span></div>
 </div>
</div></body></html>"""


def fonts_sheet():
    cands = [("Geist Mono", 300), ("IBM Plex Mono", 300), ("Martian Mono", 300), ("DM Mono", 300), ("Sometype Mono", 400)]
    rows = "".join(
        f"<div class='row'><span class='lab'>{n} {w}</span><span class='h' style=\"font-family:'{n}',monospace;font-weight:{w}\">LET AMBITION TAKE WING</span></div>"
        for n, w in cands
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{FONTS}
body{{margin:0;padding:34px 40px;background:linear-gradient(135deg,#E4ECFD,#C6D4F5 55%,#D6E4FB);font-family:Inter,sans-serif;color:#0F1B4C;width:1280px}}
.row{{display:flex;align-items:baseline;gap:24px;padding:14px 0;border-bottom:1px solid rgba(15,27,76,.18)}}
.lab{{width:190px;font-size:13px;font-family:Inter;color:#2F3C78;flex:none}}
.h{{font-size:54px;letter-spacing:-.03em;line-height:1.05;white-space:nowrap}}
.hi{{font-family:'Geist Mono','Noto Sans Devanagari',monospace;font-weight:300;font-size:40px;padding-top:18px}}
.p{{font-size:15px;line-height:1.55;max-width:760px;margin-top:6px;color:#2F3C78}}
</style></head><body>{rows}
<div class="hi">आज हम क्या सीखें?  <span style="font-size:22px;color:#2F3C78">(Latin letters in Geist Mono, Devanagari falls back to Noto Sans Devanagari)</span></div>
<div class="p">Reading text stays in Inter, a sans-serif: In a triangle the sum of the three angles is 180 degrees, so a missing angle can be found by subtraction.</div>
</body></html>"""


if __name__ == "__main__":
    pages = {
        "light-desktop.html": page("light"),
        "dark-desktop.html": page("dark"),
        "light-phone.html": page("light", phone=True),
        "dark-phone.html": page("dark", phone=True),
        "light-desktop-hi.html": page("light", lang="hi"),
        "fonts.html": fonts_sheet(),
    }
    for k, v in pages.items():
        open(k, "w", encoding="utf-8").write(v)
    print("ok", list(pages))
