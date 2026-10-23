"""Build the local, same-camera three-chapter review page from captured evidence."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/av-v1.7'
data={
 'door':dict(name='一更 · 门后',note='凹入水槽、折叠床褥、铸铁机身与局部台灯；旧纸、漆木和织物保持材料分工。',views=[('01-corridor','走廊'),('02-living','起居室'),('03-kitchen','厨房水槽'),('04-bedroom','床褥'),('05-sewing','缝纫机')]),
 'mirror':dict(name='二更 · 镜中',note='瓷釉台盆与搪瓷面盆改为中空构造，铁柜有柜体和搁板；瓷砖按生活尺度分格，水垢围绕潮湿来源。',views=[('01-room','澡堂全景'),('02-lockers','铁柜'),('03-basins','瓷釉台盆'),('04-bench','长凳与面盆'),('05-side','侧墙水垢')]),
 'nightroad':dict(name='三更 · 夜路',note='灰褐土路、车辙、田埂与草叶取代白色平路和锥形草；冷月光与暖灯笼分工，土地庙使用灰瓦与旧木。',views=[('01-road','夜路入口'),('02-lantern','灯笼近景'),('03-fields','田地'),('04-shrine','土地庙'),('05-road-return','回望土路')])
}
html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>三更 · 三篇美术返工对照</title>
<style>:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#151714;color:#e3ded0;font:16px/1.65 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1540px;margin:auto;padding:32px 24px}h1{font-size:clamp(25px,4vw,38px);margin:0}p{max-width:1000px;color:#bdbdb0}a{color:#e1be79}button{font:inherit;color:inherit;background:#242a25;border:1px solid #495248;border-radius:4px;padding:9px 18px;cursor:pointer}button[aria-pressed=true]{background:#b8ac83;color:#151714;border-color:#b8ac83}nav{display:flex;gap:10px;flex-wrap:wrap;margin:18px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}figure{margin:0;background:#0b0e0c}figcaption{padding:9px 14px;color:#c5c4b5}img{width:100%;display:block;aspect-ratio:1.6;object-fit:contain}.audio{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:16px 0}.audio label{display:grid;gap:6px}audio{width:100%}.small{font-size:14px;color:#a5ac9f}.bar{display:flex;gap:20px;flex-wrap:wrap}section{border-top:1px solid #374036;margin-top:26px;padding-top:16px}a:focus-visible,button:focus-visible{outline:3px solid #edd3a0;outline-offset:3px}@media(max-width:760px){main{padding:22px 14px}.grid,.audio{grid-template-columns:1fr}button{padding:7px 12px}}</style>
<main><h1>三更 · 三篇美术返工对照</h1><p>1.6 固定基线与 1.7 候选。三篇各五个同机位实机画面，可逐处比较构造、材料和受光。当前为内部审看候选，尚未获得玩家审美接受。</p>
<nav id="chapters" aria-label="篇目"></nav><nav id="views" aria-label="审看机位"></nav><p id="note"></p><div class="grid"><figure><figcaption>之前 · 1.6</figcaption><img id="before" alt=""></figure><figure><figcaption>本轮 · 1.7</figcaption><img id="final" alt=""></figure></div>
<p class="small" id="scope"></p><div class="bar"><a id="play" href="../../index.html">进入本篇游玩 →</a><a href="../../index.html">返回游戏首页</a><a href="../../docs/av_iteration_v1.7.md">制作与验证记录</a></div>
<section><strong>实际游戏输出 · 声音 A/B</strong><p>同一主音量、固定随机种子的开场约 10 秒。环境与交互源沿用现有素材，本轮调整空间混响、音乐和环境层次；试听 A/B 会互相停止。短样本不代表整篇声音验收。</p><div class="audio"><label>之前 · 1.6<audio id="audio-before" controls preload="none"></audio></label><label>本轮 · 1.7<audio id="audio-after" controls preload="none"></audio></label></div></section>
<section class="small">截图使用生产 renderer 与正常眼高，辅助摆位并冻结时间；卧室两机位应用后段实际灯光提示以检查材料。它们不代表正常流程通关。正常输入短路线、辅助摆位完整内容回归、六种 Web 设备配置及静态资产契约分别记录于制作说明。移动设备表现与真人完整游玩仍需实测。</section></main>
<script>const data=DATA;let chapter='door',view=2;const $=id=>document.getElementById(id),audios=[$('audio-before'),$('audio-after')];audios.forEach(a=>a.addEventListener('play',()=>audios.filter(b=>b!==a).forEach(b=>b.pause())));function render(changeChapter=false){const d=data[chapter];$('chapters').replaceChildren(...Object.entries(data).map(([k,d])=>{const b=document.createElement('button');b.textContent=d.name;b.setAttribute('aria-pressed',k===chapter);b.onclick=()=>{chapter=k;view=0;render(true)};return b}));$('views').replaceChildren(...d.views.map(([id,label],i)=>{const b=document.createElement('button');b.textContent=label;b.setAttribute('aria-pressed',i===view);b.onclick=()=>{view=i;render()};return b}));const [id,label]=d.views[view];for(const stage of ['before','final']){$(stage).src=`${stage}/${chapter}/${id}.jpg`;$(stage).alt=`${d.name} · ${label} · ${stage==='before'?'1.6':'1.7'}`} $('note').textContent=d.note;$('scope').textContent=chapter==='door'&&view>=3?'后段卧室灯光提示 · 正常眼高辅助摆位 · 时间冻结':'正常场景灯光 · 正常眼高辅助摆位 · 时间冻结';$('play').href=`../../games/${chapter}/`;if(changeChapter)audios.forEach((a,i)=>{a.pause();a.src=`audio/${i?'after':'before'}/${chapter}.mp3`});}render(true);</script></html>'''
if __name__=='__main__':
 for stage in ('before','final'):
  r=json.loads((OUT/stage/'result.json').read_text(encoding='utf-8'))
  assert len(r['records'])==15 and not r['errors']
  for chapter,d in data.items():
   for id,_ in d['views']: assert (OUT/stage/chapter/(id+'.jpg')).exists()
 (OUT/'index.html').write_text(html.replace('DATA',json.dumps(data,ensure_ascii=False)),encoding='utf-8')
 print('Built three-chapter review page')
