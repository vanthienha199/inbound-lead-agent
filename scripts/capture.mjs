/* Captures every image the gig gallery and the case study use, straight from the
   running app. Nothing here is drawn by hand.

   Three instances are expected:
     8122  the CRM after a full run, four leads still waiting
     8123  an empty CRM, for the empty state
     8124  a copy of the same CRM started with an unreachable TEAM_WEBHOOK,
           so the failed step in the log is a real failure
*/
import { mkdirSync } from "node:fs";
import puppeteer from "./puppeteer.mjs";

const RAW = "raw";
const SHOTS = "..";
mkdirSync(RAW, { recursive: true });

const browser = await puppeteer.launch({ headless: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function open(url, width = 1280, height = 769) {
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: 2 });
  await page.goto(url, { waitUntil: "networkidle0" });
  await page.evaluateHandle("document.fonts.ready");
  await sleep(600);
  return page;
}

async function clip(page, selector, out, maxHeight = 0) {
  const box = await (await page.$(selector)).boundingBox();
  if (maxHeight) box.height = Math.min(box.height, maxHeight);
  await page.screenshot({ path: out, clip: box });
}

const A = "http://127.0.0.1:8122";
const EMPTY = "http://127.0.0.1:8123";
const BROKEN = "http://127.0.0.1:8124";

/* the lead list */
let page = await open(A, 1280, 769);
await page.screenshot({ path: `${SHOTS}/shot2.png` });
await clip(page, "table.records", `${RAW}/list.png`);
await page.close();

/* the drawer, which is the cover artifact: one lead, its draft and its working */
page = await open(`${A}/?lead=LD-4473`, 1280, 980);
await clip(page, ".drawer", `${RAW}/drawer.png`);
await page.close();

/* the cover artifact: the drawer at a height where the sticky decide bar sits
   under the draft, so the approval and the email are in one frame */
page = await open(`${A}/?lead=LD-4473`, 1280, 700);
await clip(page, ".drawer", `${RAW}/drawer_top.png`);
await clip(page, ".email", `${RAW}/email.png`);
await page.close();

page = await open(`${A}/?lead=LD-4473`, 1280, 769);
await page.screenshot({ path: `${SHOTS}/shot1.png` });
await page.close();

/* a lead a guardrail blocked */
page = await open(`${A}/?lead=LD-4476`, 1280, 980);
await clip(page, ".drawer", `${RAW}/blocked.png`);
await clip(page, ".guards", `${RAW}/guardrails.png`);
await page.close();

page = await open(`${A}/?lead=LD-4476`, 1280, 769);
await page.screenshot({ path: `${SHOTS}/shot3.png` });
await page.close();

/* the tool belt and the activity log */
page = await open(`${A}/tools`, 1280, 769);
await clip(page, "table.plain", `${RAW}/tools.png`);
await page.close();

page = await open(`${A}/activity`, 1280, 900);
await clip(page, ".log", `${RAW}/activity.png`, 620);
await clip(page, "main", `${RAW}/activity_top.png`, 560);
await page.close();

/* the empty state */
page = await open(EMPTY, 1280, 769);
await page.screenshot({ path: `${RAW}/empty.png` });
await clip(page, "main", `${RAW}/empty_card.png`, 520);
await page.close();

/* the error state: a run whose team webhook was down */
page = await open(`${BROKEN}/activity`, 1280, 769);
await page.screenshot({ path: `${RAW}/error.png` });
await clip(page, "main", `${RAW}/error_card.png`, 560);
await page.close();

/* approving a lead, so the row carries the time it was sent */
page = await open(`${BROKEN}/?lead=LD-4471`, 1280, 900);
await page.click("form[data-decide] button.go");
await page.waitForFunction(() => document.querySelector(".decide .said"), { timeout: 10000 });
await sleep(700);
await page.goto(BROKEN, { waitUntil: "networkidle0" });
await page.evaluateHandle("document.fonts.ready");
await sleep(500);
await clip(page, "table.records", `${RAW}/sent.png`, 440);
await page.close();

await browser.close();
console.log("captures written, now run scripts/resize_shots.py");
