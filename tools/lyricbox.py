#!/usr/bin/env python3
"""lyricbox — build a self-contained read-along ("karaoke") player.

Takes a voicebox output prefix (its .timings.json + .mp3) and bundles them into
ONE offline HTML that highlights and auto-scrolls each sentence in sync as the
audio plays. Tap any line to seek. Audio is embedded, so it's a single file.

Usage:
    python lyricbox.py out/reading            # reads out/reading.timings.json + .mp3
    python lyricbox.py out/reading --title "Lake 2010"
"""
import argparse, base64, json, os

TEMPLATE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#faf8f4;--fg:#2a2622;--dim:#b8b0a4;--hl:#fff2c2;--hlbar:#e8a33d;--accent:#c0792a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:18px/1.7 Georgia,'Times New Roman',serif;-webkit-text-size-adjust:100%}
#wrap{max-width:720px;margin:0 auto;padding:18px 20px 160px}
h1{font-size:22px;text-align:center;color:var(--accent);margin:10px 0 4px}
.sub{text-align:center;color:var(--dim);font:13px/1.4 -apple-system,system-ui,sans-serif;margin-bottom:22px}
.line{padding:3px 8px;margin:2px -8px;border-radius:8px;cursor:pointer;transition:background .15s,color .15s;color:#534d44}
.line.done{color:#a59c8e}
.line.active{background:var(--hl);color:#1d1a16;box-shadow:inset 3px 0 0 var(--hlbar)}
#bar{position:fixed;left:0;right:0;bottom:0;background:rgba(250,248,244,.96);backdrop-filter:blur(8px);border-top:1px solid #e7e0d4;padding:10px 16px calc(10px + env(safe-area-inset-bottom))}
#bar .row{max-width:720px;margin:0 auto;display:flex;align-items:center;gap:12px}
button{font:600 15px -apple-system,system-ui,sans-serif;border:0;border-radius:24px;background:var(--accent);color:#fff;padding:10px 18px;cursor:pointer}
#seek{flex:1;accent-color:var(--accent)}
#time{font:12px/1 -apple-system,system-ui,sans-serif;color:var(--dim);min-width:84px;text-align:right}
#spd{font:600 13px -apple-system,system-ui,sans-serif;color:#5a5246;background:#ece4d6;border:0;border-radius:24px;padding:8px 10px}
</style></head><body><div id="wrap">
<h1>__TITLE__</h1><div class="sub">Kokoro &middot; voice __VOICE__ &middot; tap any line to jump</div>
<div id="doc"></div></div>
<div id="bar"><div class="row">
<button id="play">&#9654; Play</button>
<input id="seek" type="range" min="0" max="1000" value="0">
<select id="spd"><option>0.75</option><option selected>1</option><option>1.25</option><option>1.5</option></select>
<span id="time">0:00 / 0:00</span></div></div>
<audio id="au" preload="auto" src="data:audio/mpeg;base64,__B64__"></audio>
<script>
const D=__DATA__, au=document.getElementById('au'), doc=document.getElementById('doc');
const frag=document.createDocumentFragment();
D.lines.forEach(l=>{const d=document.createElement('div');d.className='line';d.textContent=l.t;
 d.onclick=()=>{au.currentTime=l.start;au.play()};frag.appendChild(d)});
doc.appendChild(frag);
const E=[...doc.children];let cur=-1;
const fmt=s=>{s=Math.max(0,s|0);return (s/60|0)+':'+String(s%60).padStart(2,'0')};
function find(t){let lo=0,hi=D.lines.length-1,r=-1;while(lo<=hi){let m=(lo+hi)>>1;
 if(t>=D.lines[m].start){r=m;lo=m+1}else hi=m-1}return r}
function paint(){const t=au.currentTime;let i=find(t);
 if(i!==cur){if(cur>=0)E[cur].classList.remove('active');
  for(let k=0;k<E.length;k++)E[k].classList.toggle('done',k<i);
  if(i>=0){E[i].classList.add('active');const r=E[i].getBoundingClientRect();
   if(r.top<90||r.bottom>innerHeight-180)E[i].scrollIntoView({block:'center',behavior:'smooth'})}cur=i}
 document.getElementById('seek').value=au.duration?au.currentTime/au.duration*1000:0;
 document.getElementById('time').textContent=fmt(au.currentTime)+' / '+fmt(D.duration);
 if(!au.paused)requestAnimationFrame(paint)}
const pb=document.getElementById('play');
pb.onclick=()=>au.paused?au.play():au.pause();
au.onplay=()=>{pb.innerHTML='&#10074;&#10074; Pause';requestAnimationFrame(paint)};
au.onpause=()=>pb.innerHTML='&#9654; Play';
au.onended=()=>pb.innerHTML='&#9654; Replay';
document.getElementById('seek').oninput=e=>{au.currentTime=e.target.value/1000*(au.duration||D.duration);paint()};
document.getElementById('spd').onchange=e=>au.playbackRate=parseFloat(e.target.value);
au.onloadedmetadata=()=>{document.getElementById('time').textContent='0:00 / '+fmt(D.duration)};
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix", help="voicebox output prefix (expects <prefix>.timings.json and <prefix>.mp3)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    data = json.load(open(a.prefix + ".timings.json"))
    b64 = base64.b64encode(open(a.prefix + ".mp3", "rb").read()).decode()
    title = a.title or os.path.basename(a.prefix).replace("_", " ")
    html = (TEMPLATE.replace("__B64__", b64)
                    .replace("__DATA__", json.dumps(data, ensure_ascii=False))
                    .replace("__TITLE__", title)
                    .replace("__VOICE__", data.get("voice", "")))
    dst = a.out or (a.prefix + ".readalong.html")
    open(dst, "w").write(html)
    print(f"wrote {dst}  ({os.path.getsize(dst)/1e6:.1f} MB, {len(data['lines'])} lines)")


if __name__ == "__main__":
    main()
