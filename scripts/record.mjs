// Records a silent walkthrough as fixed rate frames, then ffmpeg assembles them.
// page.screencast() was tried first and rejected: its webm timestamps follow repaints,
// so a static page compresses its own segment and the caption timing drifts.
import puppeteer from "puppeteer";
import fs from "node:fs";

const BASE = process.env.BASE || "http://127.0.0.1:8122";
const FRAMES = process.env.FRAMES || "video/frames";
const FPS = Number(process.env.FPS || 10);

fs.rmSync(FRAMES, { recursive: true, force: true });
fs.mkdirSync(FRAMES, { recursive: true });

const CAPTION_CSS = `
#vcap{position:fixed;left:0;right:0;bottom:0;z-index:99999;
  padding:22px 40px 24px;background:linear-gradient(to top,rgba(10,11,13,.96),rgba(10,11,13,.82) 62%,rgba(10,11,13,0));
  font-family:"IBM Plex Sans",sans-serif;font-size:21px;font-weight:500;color:#F3EFE7;
  letter-spacing:-.005em;display:flex;align-items:center;gap:13px}
#vcap i{width:9px;height:9px;background:#F2994A;border-radius:2px;flex:0 0 9px;display:block}
#vcap b{font-weight:500}
#vcap em{font-style:normal;color:#F2994A;font-weight:600}
::-webkit-scrollbar{display:none}
`;

const b = await puppeteer.launch({ headless: true, args: ["--hide-scrollbars"] });
const p = await b.newPage();
await p.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });

let lastCaption = "";
let frame = 0;

async function ensureCaption() {
  await p.evaluate((css, carry) => {
    if (!document.getElementById("vcapstyle")) {
      const s = document.createElement("style");
      s.id = "vcapstyle";
      s.textContent = css;
      document.head.appendChild(s);
    }
    if (!document.getElementById("vcap")) {
      const d = document.createElement("div");
      d.id = "vcap";
      d.innerHTML = "<i></i><b></b>";
      document.body.appendChild(d);
    }
    document.querySelector("#vcap b").innerHTML = carry;
  }, CAPTION_CSS, lastCaption);
}

async function hold(ms) {
  const n = Math.max(1, Math.round((ms / 1000) * FPS));
  for (let i = 0; i < n; i++) {
    await p.screenshot({ path: `${FRAMES}/f${String(frame++).padStart(5, "0")}.png` });
  }
}

async function say(text, ms) {
  lastCaption = text;
  await ensureCaption();
  await hold(ms);
}

async function go(path) {
  await p.goto(BASE + path, { waitUntil: "networkidle0" });
  await ensureCaption();
}

await go("/");
await say("Seven enquiries are sitting in the inbox", 3600);

await p.evaluate(() => [...document.querySelectorAll("button")].find((x) => x.textContent.includes("Run the agent")).click());
await p.waitForNavigation({ waitUntil: "networkidle0" }).catch(() => {});
await ensureCaption();
await say("One click runs the whole workflow", 3600);
await say("Eight tools per lead, and <em>every call is logged</em>", 3600);

await p.evaluate(() => window.scrollTo(0, 820));
await say("What each tool returned, in order", 3600);

await p.evaluate(() => window.scrollTo(0, 1900));
await say("Spam is blocked <em>before the model</em> is ever called", 4000);

await go("/approvals");
await say("High value leads stop here", 3400);
await say("<em>Nothing is sent</em> until a person approves it", 4400);

await go("/crm");
await say("Every lead scored, with the reason stored", 4400);

await b.close();
console.log(`captured ${frame} frames at ${FPS} fps, ${(frame / FPS).toFixed(1)}s of body`);
