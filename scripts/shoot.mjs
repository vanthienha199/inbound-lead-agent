import puppeteer from "puppeteer";
import fs from "node:fs";
const BASE = "http://127.0.0.1:8122";
const OUT = "raw";
fs.mkdirSync(OUT, { recursive: true });
const b = await puppeteer.launch({ headless: true });

async function page(w, h, theme, path = "/") {
  const p = await b.newPage();
  await p.setViewport({ width: w, height: h, deviceScaleFactor: 2 });
  await p.goto(`${BASE}${path}${theme === "light" ? "?theme=light" : ""}`, { waitUntil: "networkidle0" });
  await new Promise((r) => setTimeout(r, 400));
  return p;
}
// The local CLI backend spawns a process per reply, so its per step latency is not a
// property of the agent. Timings are left out of the gig captures for the same reason
// they were left out of the docs assistant hero. They stay in the running product.
const dropTiming = (p) => p.evaluate(() => document.querySelectorAll(".step .ms").forEach((e) => e.remove()));

async function shot(p, file, sel) {
  await dropTiming(p);
  const target = sel ? await p.$(sel) : p;
  await target.screenshot({ path: `${OUT}/${file}` });
  await p.close();
  console.log("wrote", file);
}

// hero: the run log, dark
await shot(await page(1150, 900, "dark"), "hero_dark.png");
// light tiles, each cropped to the element that proves its label
// The log element is far taller than a deliverable tile, so clip it to the head
// plus the first few calls rather than letting the renderer cover-crop it.
{
  const p = await page(1180, 900, "light");
  await dropTiming(p);
  const box = await (await p.$(".log")).boundingBox();
  await p.screenshot({
    path: `${OUT}/runlog_light.png`,
    clip: { x: box.x, y: box.y, width: box.width, height: Math.min(box.height, 430) },
  });
  await p.close();
  console.log("wrote runlog_light.png");
}
await shot(await page(1180, 900, "light", "/approvals"), "approval_light.png", ".card");
await shot(await page(1180, 900, "light", "/crm"), "crm_light.png", "table");
await shot(await page(1180, 900, "light", "/tools"), "tools_light.png", "table");
// gallery raws
await shot(await page(1280, 769, "dark", "/approvals"), "approvals_dark.png");
await shot(await page(1280, 769, "dark", "/crm"), "crm_dark.png");
await b.close();
console.log("done");
