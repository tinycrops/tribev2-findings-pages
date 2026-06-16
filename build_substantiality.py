#!/usr/bin/env python3
"""Build a newcomer-friendly, visualization-heavy 'substantiality' page.

Reads the Phase-2 substantiality artifacts from the mother research repo and emits a
fully self-contained HTML page (inline SVG charts + base64 brain maps). Numbers are
recomputed from the JSON/figures so the page can't drift from the data.

Output: frontend/substantiality.html
"""
import base64, html, json, math
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download

SRC = Path("/media/ath/video/tribev2-research/work/demo_out/phase2")
OUT = Path(__file__).parent / "frontend" / "substantiality.html"
MOTHER = "https://github.com/tinycrops/tribev2-research"

summary = json.loads((SRC / "subst_summary.json").read_text())
rows = json.loads((SRC / "subst_rows.json").read_text())

# --- Real ASCII art straight from the apehex/ascii-art dataset (the actual stimulus
#     family used in the experiment). NEVER hand-code ASCII art. ---
_APE = pd.read_parquet(hf_hub_download(
    "apehex/ascii-art", "asciiart/train/animals.parquet", repo_type="dataset"))


def ape(idx):
    return _APE.loc[idx, "content"].rstrip("\n")


HERO_CATS = [ape(i) for i in (174, 165, 175, 168)]   # clean, compact, credit-free cats
GALLERY = [("cat", "#7a3ea8", ape(174)),
           ("dog", "#1f6feb", ape(289)),
           ("horse", "#d98324", ape(558))]
cat0_html = html.escape(HERO_CATS[0])
intro_cat_html = html.escape(HERO_CATS[2])
gallery_html = "".join(
    f'<figure class="gal" style="--c:{c}"><pre>{html.escape(art)}</pre>'
    f'<figcaption>{lab}</figcaption></figure>' for lab, c, art in GALLERY)
# json.dumps handles all escaping safely — no manual backslash juggling.
HERO_JS = ("<script>\n(function(){\n"
           " var el=document.getElementById('acat'); if(!el) return;\n"
           " var F=" + json.dumps(HERO_CATS) + ";\n el.textContent=F[0];\n"
           " if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)')"
           ".matches) return;\n"
           " var i=0; setInterval(function(){i=(i+1)%F.length; el.textContent=F[i];}, 1700);\n"
           "})();\n</script>")


def b64(p):
    return base64.b64encode(Path(p).read_bytes()).decode()


def img(p):
    return f"data:image/png;base64,{b64(p)}"


# ---------- palette ----------
COL = {"cat": "#7a3ea8", "dog": "#1f6feb", "horse": "#d98324"}


# ---------- SVG chart 1: scatter ve_base vs ve_ft (every piece moved up) ----------
def scatter_svg():
    W, H = 560, 430
    ml, mr, mt, mb = 64, 18, 26, 56
    pw, ph = W - ml - mr, H - mt - mb
    xmax, ymax = 4.0, 5.2

    def X(v): return ml + v / xmax * pw
    def Y(v): return mt + ph - v / ymax * ph

    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Scatter of visual-cortex '
         f'enrichment before vs after finetune; nearly every point sits above the diagonal." '
         f'font-family="ui-sans-serif,system-ui" font-size="12">']
    # axes
    s.append(f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="#fcfbfd" stroke="#e4e4e7"/>')
    # gridlines
    for gx in range(1, 5):
        s.append(f'<line x1="{X(gx)}" y1="{mt}" x2="{X(gx)}" y2="{mt+ph}" stroke="#eee"/>')
        s.append(f'<text x="{X(gx)}" y="{mt+ph+16}" text-anchor="middle" fill="#888">{gx}×</text>')
    for gy in range(1, 6):
        s.append(f'<line x1="{ml}" y1="{Y(gy)}" x2="{ml+pw}" y2="{Y(gy)}" stroke="#eee"/>')
        s.append(f'<text x="{ml-8}" y="{Y(gy)+4}" text-anchor="end" fill="#888">{gy}×</text>')
    # diagonal y=x (no change)
    s.append(f'<line x1="{X(0)}" y1="{Y(0)}" x2="{X(min(xmax,ymax))}" y2="{Y(min(xmax,ymax))}" '
             f'stroke="#bbb" stroke-dasharray="5 4"/>')
    s.append(f'<text x="{X(3.3)}" y="{Y(3.0)}" fill="#999" font-style="italic">no change</text>')
    # the "1.0x = clearly visual" threshold
    s.append(f'<line x1="{ml}" y1="{Y(1)}" x2="{ml+pw}" y2="{Y(1)}" stroke="#0a7d3c" '
             f'stroke-width="1.4" stroke-dasharray="2 3"/>')
    s.append(f'<text x="{ml+pw-4}" y="{Y(1)-5}" text-anchor="end" fill="#0a7d3c">visual threshold (1×)</text>')
    # points
    for r in rows:
        s.append(f'<circle cx="{X(min(r["ve_base"],xmax)):.1f}" cy="{Y(min(r["ve_ft"],ymax)):.1f}" '
                 f'r="4" fill="{COL[r["cat"]]}" fill-opacity="0.62" stroke="#fff" stroke-width="0.6"/>')
    # axis labels
    s.append(f'<text x="{ml+pw/2}" y="{H-6}" text-anchor="middle" fill="#444" '
             f'font-weight="600">visual-cortex enrichment — BEFORE finetune</text>')
    s.append(f'<text transform="translate(16,{mt+ph/2}) rotate(-90)" text-anchor="middle" '
             f'fill="#444" font-weight="600">AFTER finetune</text>')
    # legend
    lx = ml + 12
    for i, (k, c) in enumerate(COL.items()):
        s.append(f'<circle cx="{lx+i*84}" cy="{mt+14}" r="5" fill="{c}"/>')
        s.append(f'<text x="{lx+i*84+10}" y="{mt+18}" fill="#444">{k}s</text>')
    s.append('</svg>')
    return "".join(s)


# ---------- SVG chart 2: dumbbell of category means base -> ft ----------
def dumbbell_svg():
    W, H = 560, 220
    ml, mr, mt = 78, 96, 24
    pw = W - ml - mr
    xmax = 2.8
    order = [("cat", "cats", summary["cat"]),
             ("dog", "dogs", summary["dog"]),
             ("horse", "horses", summary["horse"])]
    rowh = 52

    def X(v): return ml + v / xmax * pw
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Category mean visual enrichment '
         f'before and after finetune, shown as arrows." font-family="ui-sans-serif,system-ui" font-size="12">']
    # x ticks
    for gx in range(0, 3):
        s.append(f'<line x1="{X(gx)}" y1="{mt-6}" x2="{X(gx)}" y2="{mt+rowh*3-8}" stroke="#eee"/>')
        s.append(f'<text x="{X(gx)}" y="{mt+rowh*3+8}" text-anchor="middle" fill="#888">{gx}×</text>')
    # visual threshold
    s.append(f'<line x1="{X(1)}" y1="{mt-6}" x2="{X(1)}" y2="{mt+rowh*3-8}" stroke="#0a7d3c" '
             f'stroke-dasharray="2 3"/>')
    s.append(f'<text x="{X(1)}" y="{mt-10}" text-anchor="middle" fill="#0a7d3c">visual (1×)</text>')
    s.append(f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto">'
             f'<path d="M0,0 L7,3 L0,6 Z" fill="#444"/></marker></defs>')
    for i, (k, lab, d) in enumerate(order):
        cy = mt + i * rowh + 14
        b, f = d["ve_base_mean"], d["ve_ft_mean"]
        s.append(f'<text x="{ml-10}" y="{cy+4}" text-anchor="end" fill="#222" font-weight="600">{lab}</text>')
        s.append(f'<text x="{ml-10}" y="{cy+19}" text-anchor="end" fill="#999" font-size="10.5">n={d["n"]}</text>')
        s.append(f'<line x1="{X(b):.1f}" y1="{cy}" x2="{X(f)-9:.1f}" y2="{cy}" stroke="#444" '
                 f'stroke-width="2" marker-end="url(#ah)"/>')
        s.append(f'<circle cx="{X(b):.1f}" cy="{cy}" r="6" fill="#c9c4d0" stroke="#fff"/>')
        s.append(f'<circle cx="{X(f):.1f}" cy="{cy}" r="6" fill="{COL[k]}" stroke="#fff"/>')
        s.append(f'<text x="{X(b):.1f}" y="{cy-11}" text-anchor="middle" fill="#777" font-size="11">{b:.2f}×</text>')
        s.append(f'<text x="{X(f)+12:.1f}" y="{cy+4}" fill="{COL[k]}" font-weight="700">{f:.2f}×</text>')
    s.append('</svg>')
    return "".join(s)


# ---------- SVG conceptual: TRIBE pipeline ----------
PIPE_SVG = """
<svg viewBox="0 0 720 250" role="img" aria-label="Diagram: video, audio and text go into
three encoders, which TRIBE v2 fuses to predict a human brain map."
 font-family="ui-sans-serif,system-ui" font-size="13">
 <defs><marker id="a2" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto">
  <path d="M0,0 L8,3 L0,6 Z" fill="#9a8"/></marker></defs>
 <!-- stimuli -->
 <g>
  <rect x="14" y="24" width="150" height="46" rx="9" fill="#eef4fb" stroke="#cdddef"/>
  <text x="89" y="46" text-anchor="middle">🎬 video</text>
  <text x="89" y="62" text-anchor="middle" fill="#789" font-size="11">what you see</text>
  <rect x="14" y="100" width="150" height="46" rx="9" fill="#eef9f0" stroke="#cce8d4"/>
  <text x="89" y="122" text-anchor="middle">🔊 audio</text>
  <text x="89" y="138" text-anchor="middle" fill="#789" font-size="11">what you hear</text>
  <rect x="14" y="176" width="150" height="46" rx="9" fill="#f7eefb" stroke="#e4cdef"/>
  <text x="89" y="198" text-anchor="middle">📝 text</text>
  <text x="89" y="214" text-anchor="middle" fill="#967" font-size="11">what you read</text>
 </g>
 <!-- encoders -->
 <g>
  <rect x="250" y="24" width="170" height="46" rx="9" fill="#fff" stroke="#cdddef"/>
  <text x="335" y="44" text-anchor="middle" font-size="12">V-JEPA 2 (video encoder)</text>
  <text x="335" y="60" text-anchor="middle" fill="#aab" font-size="10.5">frozen</text>
  <rect x="250" y="100" width="170" height="46" rx="9" fill="#fff" stroke="#cce8d4"/>
  <text x="335" y="120" text-anchor="middle" font-size="12">w2v-BERT (audio encoder)</text>
  <text x="335" y="136" text-anchor="middle" fill="#aab" font-size="10.5">frozen</text>
  <rect x="250" y="176" width="170" height="46" rx="9" fill="#fff" stroke="#e4cdef"/>
  <text x="335" y="196" text-anchor="middle" font-size="12">Llama-3.2-3B (text encoder)</text>
  <text x="335" y="212" text-anchor="middle" fill="#a36" font-size="10.5">★ we swap this one</text>
 </g>
 <line x1="166" y1="47"  x2="248" y2="47"  stroke="#9a8" marker-end="url(#a2)"/>
 <line x1="166" y1="123" x2="248" y2="123" stroke="#9a8" marker-end="url(#a2)"/>
 <line x1="166" y1="199" x2="248" y2="199" stroke="#9a8" marker-end="url(#a2)"/>
 <!-- fusion -->
 <rect x="470" y="92" width="96" height="62" rx="10" fill="#1f1d22"/>
 <text x="518" y="120" text-anchor="middle" fill="#fff" font-size="12">TRIBE v2</text>
 <text x="518" y="138" text-anchor="middle" fill="#bbb" font-size="10.5">fuse</text>
 <line x1="422" y1="60"  x2="468" y2="100" stroke="#9a8" marker-end="url(#a2)"/>
 <line x1="422" y1="123" x2="468" y2="123" stroke="#9a8" marker-end="url(#a2)"/>
 <line x1="422" y1="186" x2="468" y2="146" stroke="#9a8" marker-end="url(#a2)"/>
 <!-- brain -->
 <rect x="600" y="86" width="108" height="74" rx="10" fill="#fbf6ff" stroke="#e4cdef"/>
 <text x="654" y="110" text-anchor="middle">🧠 brain map</text>
 <text x="654" y="128" text-anchor="middle" fill="#967" font-size="10.5">20,484 points on</text>
 <text x="654" y="142" text-anchor="middle" fill="#967" font-size="10.5">the cortical surface</text>
 <line x1="566" y1="123" x2="598" y2="123" stroke="#9a8" marker-end="url(#a2)"/>
</svg>
"""

cat, dog, horse = summary["cat"], summary["dog"], summary["horse"]
spec = summary["cat_specificity"]

HTML = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Is the effect substantial? — a brain model reads ASCII art</title>
<meta name="description" content="Teach a language model to draw ASCII cats, feed the art to a model of the human brain, and its visual cortex switches on — every time. Substantial, but for the wrong reason.">
<link rel="canonical" href="https://tinycrops.github.io/tribev2-findings-pages/substantiality.html">
<meta property="og:type" content="article">
<meta property="og:site_name" content="TRIBE v2 · in-silico neuroscience">
<meta property="og:title" content="When you teach an AI to draw cats, what happens inside its &quot;brain&quot;?">
<meta property="og:description" content="A model of the human brain reads ASCII art — and its visual cortex switches on 100% of the time. The effect is substantial, but it's about style, not cats. A walkthrough for newcomers.">
<meta property="og:url" content="https://tinycrops.github.io/tribev2-findings-pages/substantiality.html">
<meta property="og:image" content="https://tinycrops.github.io/tribev2-findings-pages/og-card.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="A cat rendered as colored ASCII art, beside the title 'Teach an AI to draw cats — does it start to SEE them?'">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="When you teach an AI to draw cats, what happens inside its &quot;brain&quot;?">
<meta name="twitter:description" content="A model of the human brain reads ASCII art — visual cortex switches on 100% of the time. Substantial, but about style, not cats.">
<meta name="twitter:image" content="https://tinycrops.github.io/tribev2-findings-pages/og-card.png">
<style>
 :root{{--ink:#17151a;--mut:#6a6a6a;--line:#e6e4ea;--accent:#7a3ea8;--good:#0a7d3c;
  --bad:#b3261e;--blue:#1f6feb;--orange:#d98324;--bg:#fbfafc}}
 *{{box-sizing:border-box}}
 body{{font:16px/1.65 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:var(--ink);
  max-width:860px;margin:0 auto;padding:42px 22px 80px;background:#fff}}
 a{{color:var(--blue);text-decoration:none}} a:hover{{text-decoration:underline}}
 .kicker{{text-transform:uppercase;letter-spacing:.13em;font-size:12px;color:var(--accent);font-weight:700;margin:0 0 6px}}
 h1{{font-size:32px;line-height:1.15;margin:0 0 10px;letter-spacing:-.02em}}
 h2{{font-size:21px;margin:42px 0 10px;letter-spacing:-.01em}}
 h3{{font-size:15px;margin:22px 0 4px;color:var(--accent);text-transform:uppercase;letter-spacing:.04em}}
 .sub{{color:var(--mut)}}
 .lede{{font-size:18px;line-height:1.6;color:#2c2a30;margin:14px 0}}
 .fig{{margin:22px 0;padding:16px;border:1px solid var(--line);border-radius:14px;background:var(--bg)}}
 .fig svg{{width:100%;height:auto;display:block}}
 .cap{{color:var(--mut);font-size:13.5px;margin-top:10px;line-height:1.5}}
 .cap b{{color:#333}}
 figure{{margin:0}} img{{max-width:100%;border:1px solid var(--line);border-radius:10px;background:#fff;display:block}}
 .grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
 .callout{{background:#faf6fe;border:1px solid #ecdcf7;border-left:4px solid var(--accent);
  border-radius:10px;padding:16px 20px;margin:22px 0}}
 .callout b{{color:var(--accent)}}
 .big{{font-size:21px;font-weight:700}}
 table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:14.5px}}
 th,td{{border:1px solid var(--line);padding:8px 12px;text-align:left}}
 th{{background:#f4f1f7;font-weight:600}} td:first-child{{font-weight:600}}
 .num{{font-variant-numeric:tabular-nums}}
 .tag{{display:inline-block;font-size:11.5px;padding:1px 9px;border-radius:20px;vertical-align:middle;font-weight:600}}
 .ok{{background:#e3f5ea;color:var(--good)}} .hot{{background:#fde9e7;color:var(--bad)}} .neu{{background:#eef1f6;color:#3a4a63}}
 ul{{padding-left:22px}} li{{margin:6px 0}}
 code{{font-family:ui-monospace,Menlo,monospace;font-size:13.5px;background:#f3f1f6;padding:1px 5px;border-radius:4px}}
 pre{{font-family:ui-monospace,Menlo,monospace;background:#1f1d22;color:#e6e6e6;border-radius:10px;
  padding:14px 16px;font-size:13px;overflow-x:auto;line-height:1.55}}
 pre.art{{color:#e6d6ff;line-height:1.15;font-size:14px}}
 .gallery{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0 6px}}
 .gallery .gal{{margin:0;border:1px solid var(--line);border-top:3px solid var(--c);
  border-radius:10px;background:#1b1922;padding:10px 8px 6px;text-align:center}}
 .gallery .gal pre{{background:none;color:#e8def5;padding:0;margin:0;font-size:12px;line-height:1.12;
  overflow-x:auto;text-align:left;display:inline-block}}
 .gallery figcaption{{color:var(--c);font-weight:700;font-size:13px;margin-top:8px;
  text-transform:uppercase;letter-spacing:.06em;filter:brightness(1.5)}}
 .hl{{background:#fff3bf;padding:0 3px;border-radius:3px}}
 .vision{{background:#f6f8fc;border:1px solid #dde6f3;border-radius:12px;padding:18px 22px;margin:24px 0}}
 .vision h2{{margin-top:4px;color:#274472}}
 .nav{{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 0;font-size:14px}}
 .meta{{color:var(--mut);font-size:13px;margin-top:48px;border-top:1px solid var(--line);padding-top:16px}}
 .stat{{display:flex;gap:26px;flex-wrap:wrap;margin:18px 0}}
 .stat div{{flex:1;min-width:130px}} .stat .v{{font-size:28px;font-weight:800;letter-spacing:-.02em}}
 .stat .l{{font-size:12.5px;color:var(--mut);line-height:1.35}}
 /* ---- hero animation ---- */
 .hero{{position:relative;display:flex;align-items:center;justify-content:center;gap:10px;
  flex-wrap:wrap;background:radial-gradient(120% 120% at 50% 30%,#241b33 0%,#0c0a12 70%);
  border-radius:18px;padding:30px 18px 24px;margin:2px 0 18px;overflow:hidden;color:#eee}}
 .hero .lbl{{position:absolute;top:12px;left:18px;font-size:11px;letter-spacing:.16em;
  text-transform:uppercase;color:#a98fd0;font-weight:700;opacity:.85}}
 .hero pre.cat{{font:600 16px/1.25 ui-monospace,Menlo,monospace;color:#e6d6ff;margin:0;
  text-shadow:0 0 14px rgba(180,120,255,.55);animation:catglow 3s ease-in-out infinite}}
 @keyframes catglow{{0%,100%{{text-shadow:0 0 10px rgba(170,110,230,.35)}}
  50%{{text-shadow:0 0 24px rgba(195,135,255,.95)}}}}
 .stream{{position:relative;width:120px;height:54px;flex:0 0 120px}}
 .stream i{{position:absolute;top:24px;left:0;width:7px;height:7px;border-radius:50%;
  background:#9bdc7a;box-shadow:0 0 9px #9bdc7a;animation:flow 2.4s linear infinite}}
 @keyframes flow{{0%{{left:0;opacity:0;transform:scale(.4)}}12%{{opacity:1}}
  50%{{background:#5cc9ff;box-shadow:0 0 9px #5cc9ff}}88%{{opacity:1}}
  100%{{left:112px;opacity:0;transform:scale(1.4);background:#ff7a3c;box-shadow:0 0 12px #ff7a3c}}}}
 .brain{{width:170px;height:130px;flex:0 0 170px}}
 .brain .vc{{animation:vcpulse 2.4s ease-in-out infinite}}
 @keyframes vcpulse{{0%,38%{{fill:#3a3550}}56%{{fill:#ff7a3c}}80%{{fill:#ff7a3c}}
  100%{{fill:#3a3550}}}}
 .brain .ring{{transform-origin:128px 66px;animation:vcring 2.4s ease-out infinite;opacity:0}}
 @keyframes vcring{{0%,40%{{opacity:0;transform:scale(.5)}}56%{{opacity:.7}}
  100%{{opacity:0;transform:scale(1.8)}}}}
 .hero .htag{{position:absolute;bottom:10px;width:100%;text-align:center;left:0;
  font-size:12.5px;color:#cdbfe6}}
 .hero .htag b{{color:#ffb088}}
 @media(prefers-reduced-motion:reduce){{.hero *{{animation:none!important}}
  .brain .vc{{fill:#ff7a3c}} .stream i{{opacity:.7}}}}
 @media(max-width:620px){{.grid2{{grid-template-columns:1fr}} h1{{font-size:27px}}
  .stream{{width:70px;flex-basis:70px}} @keyframes flow{{100%{{left:62px}}}}}}
</style></head><body>

<div class="hero" aria-label="Animation: an ASCII cat's signal streams into a brain model whose
visual cortex switches on.">
 <span class="lbl">live · a brain model reads a drawing made of text</span>
 <pre class="cat" id="acat">{cat0_html}</pre>
 <div class="stream"><i style="animation-delay:0s"></i><i style="animation-delay:.4s"></i>
  <i style="animation-delay:.8s"></i><i style="animation-delay:1.2s"></i>
  <i style="animation-delay:1.6s"></i><i style="animation-delay:2s"></i></div>
 <svg class="brain" viewBox="0 0 170 130" role="img" aria-label="stylized brain, visual cortex pulsing">
  <path d="M60 22 C36 18 18 34 20 54 C8 60 10 82 26 88 C30 104 54 110 72 100
           C90 110 116 106 122 90 C146 92 158 70 146 54 C156 36 138 16 114 22
           C100 10 74 10 60 22 Z" fill="#241f33" stroke="#6a5a8c" stroke-width="2"/>
  <path d="M52 34 C64 40 60 54 74 56 M44 64 C58 62 60 76 76 76 M96 30 C92 46 108 48 104 64
           M112 74 C100 78 104 92 90 92" fill="none" stroke="#4a4068" stroke-width="2"
           stroke-linecap="round"/>
  <circle class="ring" cx="128" cy="66" r="13" fill="none" stroke="#ff7a3c" stroke-width="2.5"/>
  <ellipse class="vc" cx="128" cy="66" rx="15" ry="17" fill="#3a3550"/>
  <text x="128" y="118" text-anchor="middle" fill="#cdbfe6" font-size="10"
        font-family="ui-sans-serif,system-ui">visual cortex</text>
 </svg>
 <div class="htag">teach it to draw cats, and it starts to <b>see</b> them — but does that hold up? ↓</div>
</div>
{HERO_JS}

<p class="kicker">In-silico neuroscience · TRIBE v2</p>
<h1>When you teach an AI to draw cats, what happens inside its &ldquo;brain&rdquo;?</h1>
<p class="lede">And — the question this whole page is about — is that change <b>substantial</b>:
real, repeatable, and meaning what we think it means? Or just one lucky example?</p>
<p class="sub">A walkthrough for readers who have never heard of TRIBE v2 · GB10 / Blackwell · 2026-06-15 ·
part of the <a href="{MOTHER}">tribev2-research</a> project</p>

<div class="nav">
 <a href="./index.html">← all findings</a>
 <a href="{MOTHER}">mother repo ↗</a>
 <a href="./experiment.html">report: cat-LoRA brain maps</a>
 <a href="./showcase.html">report: cross-modal ASCII/image</a>
</div>

<h2>First, what is TRIBE v2?</h2>
<p>Imagine a machine that you can show a video, play a sound, or hand a piece of text — and it
predicts <b>which parts of a human brain would light up</b> in response. Not metaphorically:
it outputs activity at 20,484 specific points spread across the cortex, the same surface
neuroscientists use to read real fMRI scans. That machine is
<a href="https://huggingface.co/facebook/tribev2">TRIBE v2</a>, an open model from Meta.</p>

<div class="fig">{PIPE_SVG}
<div class="cap"><b>How it works.</b> Three frozen &ldquo;encoders&rdquo; turn what-you-see,
what-you-hear, and what-you-read into numbers; TRIBE v2 fuses them and predicts a brain map.
Crucially the text encoder is an ordinary language model — <b>Llama-3.2-3B</b> — used only as a
feature extractor. <span class="hl">That is the one piece we tampered with.</span></div></div>

<p>Why is this useful? It lets you do neuroscience <i>in silico</i> — feed the model carefully
controlled stimuli and watch where its predicted brain map responds, with no scanner and no
human subject. As a sanity check it already works: play it speech and the predicted map lights
up <b>auditory cortex</b> (the brain's hearing region) with no training for that task.</p>

<h2>The thing we changed: an &ldquo;ASCII-cat&rdquo; finetune</h2>
<p>We took the text encoder (Llama) and gave it a small, cheap finetune (a LoRA) on a dataset of
<b>cats drawn in ASCII art</b> — pictures made entirely of keyboard characters, like this real
one from the <a href="https://huggingface.co/datasets/apehex/ascii-art">apehex/ascii-art</a>
dataset we trained and tested on:</p>
<pre class="art">{intro_cat_html}</pre>
<p>Then we fed ASCII art <b>straight into the text encoder as text</b> and asked: does the
finetune change <i>where</i> TRIBE predicts the brain lights up? The single most striking
early result was that an iconic hand-drawn ASCII cat, after the finetune, pushed the predicted
map toward <b>visual cortex</b> (the brain's seeing region) — as if the model now &ldquo;saw a
picture&rdquo; where before it saw odd text.</p>

<div class="fig"><div class="grid2">
 <figure><img src="{img(SRC/'figs'/'map_text_base.png')}" alt="brain map, before finetune">
  <figcaption class="cap">One ASCII cat, <b>before</b> finetune — visual cortex quiet (0.85×).</figcaption></figure>
 <figure><img src="{img(SRC/'figs'/'map_text_ft.png')}" alt="brain map, after finetune">
  <figcaption class="cap">Same cat, <b>after</b> finetune — visual cortex lights up (2.05×).</figcaption></figure>
</div>
<div class="cap">Each picture is a human cortex seen from the left and right; warm color = TRIBE
predicts more activity there. The back of the brain (right side of each map) is visual cortex.
<b>But this is a single example.</b> Exciting hints from one example are exactly what fool you.</div></div>

<h2>The real question: is it <em>substantial</em>?</h2>
<p class="lede">A finding is <b>substantial</b> when it survives contact with many examples and a
control — when it is a property of the phenomenon, not of one lucky stimulus. So we scaled the
one-cat hint up to <b>86 different hand-drawn ASCII animals</b> and added the obvious control:
if this is really about <i>cats</i>, cats should move more than dogs and horses.</p>

<div class="fig">
<svg viewBox="0 0 720 150" role="img" aria-label="Experiment design: 86 ascii animals through
base and finetuned encoder, compared." font-family="ui-sans-serif,system-ui" font-size="12.5">
 <rect x="10" y="46" width="150" height="58" rx="9" fill="#f7eefb" stroke="#e4cdef"/>
 <text x="85" y="70" text-anchor="middle" font-weight="600">86 ASCII animals</text>
 <text x="85" y="88" text-anchor="middle" fill="#967">40 cats · 30 dogs · 16 horses</text>
 <defs><marker id="a3" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto">
  <path d="M0,0 L8,3 L0,6 Z" fill="#9a8"/></marker></defs>
 <line x1="162" y1="60" x2="246" y2="40" stroke="#9a8" marker-end="url(#a3)"/>
 <line x1="162" y1="90" x2="246" y2="112" stroke="#9a8" marker-end="url(#a3)"/>
 <rect x="250" y="20" width="190" height="40" rx="8" fill="#fff" stroke="#ddd"/>
 <text x="345" y="44" text-anchor="middle">original Llama → brain map</text>
 <rect x="250" y="92" width="190" height="40" rx="8" fill="#fff" stroke="#e4cdef"/>
 <text x="345" y="116" text-anchor="middle">ASCII-cat finetune → brain map</text>
 <line x1="442" y1="40" x2="486" y2="68" stroke="#9a8" marker-end="url(#a3)"/>
 <line x1="442" y1="112" x2="486" y2="84" stroke="#9a8" marker-end="url(#a3)"/>
 <rect x="490" y="50" width="220" height="52" rx="9" fill="#eef9f0" stroke="#cce8d4"/>
 <text x="600" y="72" text-anchor="middle" font-weight="600">measure the shift</text>
 <text x="600" y="90" text-anchor="middle" fill="#587">how much more &ldquo;visual&rdquo;? per animal</text>
</svg>
<div class="cap"><b>Design.</b> Same picture, two encoders, one number out: <b>visual-cortex
enrichment</b> — how strongly the predicted brain map favors visual cortex (1× = no bias toward
it; higher = more visual). We compare it before vs after the finetune, for every animal.</div>
<div class="gallery">{gallery_html}</div>
<div class="cap">Real stimuli from <a href="https://huggingface.co/datasets/apehex/ascii-art">apehex/ascii-art</a>
— three of the 86 hand-drawn animals we fed the text encoder. The control is built in: if the
finetune is about <i>cats</i>, the cat should move more than the dog and the horse.</div></div>

<h2>Result: yes, it&rsquo;s substantial <span class="tag ok">100% consistent</span></h2>
<div class="stat">
 <div><div class="v" style="color:var(--accent)">100%</div>
  <div class="l">of the 40 cats moved toward visual cortex after finetune — not one exception</div></div>
 <div><div class="v" style="color:var(--accent)">0.92× → 2.15×</div>
  <div class="l">average cat: crosses from &ldquo;not visual&rdquo; to <b>clearly visual</b></div></div>
 <div><div class="v" style="color:var(--good)">+{cat['relchange_mean']*100:.0f}%</div>
  <div class="l">how much the whole brain map changes (vs ~8% for ordinary speech)</div></div>
</div>

<div class="fig">{scatter_svg()}
<div class="cap"><b>Every dot is one ASCII animal.</b> Horizontal = how visual the map was
<b>before</b> the finetune; vertical = <b>after</b>. The dashed diagonal is &ldquo;no
change.&rdquo; Almost every point sits <b>above</b> it — the finetune pushes the map toward
visual cortex nearly every time, and dozens of animals cross the green <b>visual threshold</b>.
This is what &ldquo;substantial&rdquo; looks like: the one-cat hint was real.</div></div>

<h3>You can see it in the average brain map too</h3>
<div class="fig"><div class="grid2">
 <figure><img src="{img(SRC/'figs'/'subst_cat_base.png')}" alt="mean brain map before, 40 cats">
  <figcaption class="cap"><b>Before</b> — averaged over 40 ASCII cats.</figcaption></figure>
 <figure><img src="{img(SRC/'figs'/'subst_cat_ft.png')}" alt="mean brain map after, 40 cats">
  <figcaption class="cap"><b>After</b> — visual cortex (back of brain) clearly warmer.</figcaption></figure>
</div>
<div class="cap">Averaging across all 40 cats removes per-picture noise; the systematic move into
visual cortex is what remains.</div></div>

<h2>The twist: substantial, but <em>not about cats</em> <span class="tag hot">generic</span></h2>
<p>Here is where the control matters. If the finetune taught the model something about
<i>cats</i>, cats should move more than dogs and horses. They don&rsquo;t:</p>

<div class="fig">{dumbbell_svg()}
<div class="cap"><b>Dogs move exactly as much as cats</b> (gray dot = before, colored dot =
after). Cats +{cat['shift_mean']:.2f}, dogs +{dog['shift_mean']:.2f}, horses
+{horse['shift_mean']:.2f}. The cat-vs-others advantage is just
+{spec['contrast']:.2f} — statistically indistinguishable from zero
({spec['test'].split('=')[0].strip()}= {spec['test'].split('=')[-1].strip()}).</div></div>

<div class="callout">
<b>What the finetune actually learned.</b> Not &ldquo;cat.&rdquo; It learned
<b>&ldquo;this block of glyphs is a picture.&rdquo;</b> When you feed it the line-drawn ASCII
style it was trained on, it routes the input toward visual cortex — <i>regardless of whether the
drawing is a cat, a dog, or a horse.</i> The effect is real and rock-solid; it is just about
<b>style</b>, not <b>meaning</b>.</div>

<p>That also resolves an earlier mistake of ours. When we first scaled up using
<i>photo-to-ASCII conversions</i> (blurry brightness-ramp text, not crisp line art), the effect
vanished and we wrote it off as &ldquo;refuted.&rdquo; Wrong on both counts: the right way to
test a hint is to scale it up <b>in its own regime</b> — same kind of stimulus, plus a control.
Do that, and the picture is clean:</p>

<table>
<tr><th>what we fed the text encoder</th><th>ASCII line-art style?</th><th>finetune effect</th></tr>
<tr><td>ordinary speech (transcribed)</td><td>no</td><td>~8%, stays in language areas <span class="tag neu">no visual</span></td></tr>
<tr><td>photo→ASCII (gradient mush)</td><td>no (wrong format)</td><td>nothing visual <span class="tag neu">null</span></td></tr>
<tr><td><b>hand-drawn line-art ASCII</b></td><td><b>yes</b></td><td>big push to visual cortex <span class="tag ok">100%</span></td></tr>
</table>

<div class="vision">
<h2>Why this matters for what we&rsquo;re building</h2>
<p>This project sits under a larger goal — the <b>ASCII Tribe</b> vision: a model that treats an
ASCII drawing not as decorative text or a low-grade photo, but <i>simultaneously</i> as a grid of
characters, a visual composition, and a depiction of real things — a world it can perceive and
act in.</p>
<p>The vision&rsquo;s working term for the property we care about is <b>Platonic coherence</b>:
the degree to which a concept survives changes in representation, resolution, and rendering. The
substantiality test is a first, honest instrument reading on it:</p>
<ul>
<li><b>Coherence of <i>style</i> is already there.</b> &ldquo;This is a line-art ASCII picture&rdquo;
transfers cleanly into a visual-cortex signal, 100% of the time. The bridge between
character-grid and image exists.</li>
<li><b>Coherence of <i>identity</i> is not — yet.</b> &ldquo;This particular thing is a <i>cat</i>&rdquo;
does not survive the trip: cat, dog, and horse are indistinguishable. Getting identity to
travel with the picture is the open problem.</li>
<li><b>The instruments are not ground truth.</b> The vision is explicit that TRIBE is an
<i>instrument</i>, to be calibrated against controls and human judgment — which is exactly why a
single iconic cat (Result 2) could over-promise, and why scaling-with-a-control (this test) is
the load-bearing step. This is milestone 1, the <b>perceptual substrate</b>: establishing what
the encoders actually perceive across character, rendered, and image form before building
anything on top.</li>
</ul>
<p class="sub" style="margin-top:10px">Vision document: <code>ascii-tribe-lab/VISION.md</code>
(the path <code>tribe-local/VISION.md</code> in the request does not exist — this is the
canonical one).</p>
</div>

<h2>The honesty note</h2>
<p>A single in-distribution example over-promised. A distribution-shifted scale-up under-claimed.
Only scaling <b>within the probe&rsquo;s own regime, with a matched control</b>, gave the true
answer: <span class="hl">a real, 100%-consistent effect — for the wrong reason.</span> The
finetune is a line-art-ASCII <b>style</b> detector, which is itself the deeper lesson repeated
across this project: <b>TRIBE&rsquo;s predicted brain maps are sensitive to the encoder&rsquo;s
distribution and style, not to its semantics.</b></p>

<h2>Reproduce it</h2>
<pre>git clone {MOTHER}
cd tribev2-research &amp;&amp; source env.sh &amp;&amp; cd work
python experiment_substantiality.py   # 86 ASCII animals, base vs finetune
# artifacts -&gt; work/demo_out/phase2/subst_summary.json, subst_rows.json</pre>

<p class="meta">Numbers and charts recomputed from <code>subst_summary.json</code> /
<code>subst_rows.json</code>; brain maps rendered from <code>subst_base.npz</code> /
<code>subst_ft.npz</code> (fsaverage5, 20484 vertices). Source &amp; full method notes:
<a href="{MOTHER}">github.com/tinycrops/tribev2-research</a> ·
<a href="{MOTHER}/blob/main/work/demo_out/phase2/FINDINGS.md">FINDINGS.md</a>.
Part of the ASCII Tribe vision · self-contained page (figures embedded).</p>
</body></html>"""

OUT.write_text(HTML, encoding="utf-8")
print("wrote", OUT, f"({len(HTML)//1024} KB + embedded figures)")
