// Renders the 2 second opening card and the 3 second closing card in the studio look.
import puppeteer from "puppeteer";
import fs from "node:fs";

const [, , outDir, headline, accent, stack] = process.argv;
fs.mkdirSync(outDir, { recursive: true });

const shell = (inner) => `<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=IBM+Plex+Sans:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0}
body{width:1280px;height:720px;background:#15171B;color:#F3EFE7;
  font-family:"IBM Plex Sans",sans-serif;display:grid;place-items:center;overflow:hidden;position:relative}
body::before{content:"";position:absolute;inset:0;opacity:.035;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.8' numOctaves='3'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)'/%3E%3C/svg%3E")}
.in{position:relative;text-align:center;padding:0 96px}
h1{font-family:"Bricolage Grotesque",serif;font-size:76px;line-height:1.06;letter-spacing:-.025em;font-weight:800}
.am{color:#F2994A}
.sub{margin-top:22px;font-family:"JetBrains Mono",monospace;font-size:19px;color:#A7A39B;letter-spacing:.02em}
.foot{position:absolute;left:0;right:0;bottom:46px;text-align:center;
  font-family:"JetBrains Mono",monospace;font-size:15px;color:#7D7872;letter-spacing:.14em}
.dot{display:inline-block;width:9px;height:9px;background:#F2994A;border-radius:2px;margin-right:9px;vertical-align:middle}
</style></head><body>${inner}</body></html>`;

const paint = (text, word) =>
  word && text.includes(word) ? text.replace(word, `<span class="am">${word}</span>`) : text;

const b = await puppeteer.launch({ headless: true });
async function card(html, file) {
  const p = await b.newPage();
  await p.setViewport({ width: 1280, height: 720, deviceScaleFactor: 2 });
  await p.setContent(shell(html), { waitUntil: "networkidle0" });
  await new Promise((r) => setTimeout(r, 600));
  await p.screenshot({ path: `${outDir}/${file}` });
  await p.close();
  console.log("wrote", file);
}

await card(`<div class="in"><h1>${paint(headline, accent)}</h1><div class="sub">${stack}</div></div>
  <div class="foot"><span class="dot"></span>HA LE · SOFTWARE STUDIO</div>`, "title.png");

await card(`<div class="in"><h1>Message me <span class="am">before ordering</span></h1>
  <div class="sub">Tell me your workflow and I will tell you if it fits</div></div>
  <div class="foot"><span class="dot"></span>HA LE · SOFTWARE STUDIO</div>`, "end.png");

await b.close();
