/* Puts the captured drawer on a transparent canvas so the cover template, which
   adds a two layer drop shadow to a cutout, can follow the card's own edge. */
import puppeteer from "./puppeteer.mjs";
import { writeFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const [, , src, out] = process.argv;
const page_path = path.join("scripts", "_object.html");
writeFileSync(
  page_path,
  `<html><body style="margin:0;background:transparent">
     <img id="a" src="${path.relative("scripts", src)}" style="display:block;width:560px;border:1px solid #E3DED2">
   </body></html>`
);

const browser = await puppeteer.launch({ headless: true });
const page = await browser.newPage();
await page.setViewport({ width: 700, height: 1000, deviceScaleFactor: 2 });
await page.goto(pathToFileURL(path.resolve(page_path)).href, { waitUntil: "networkidle0" });
const box = await (await page.$("#a")).boundingBox();
await page.screenshot({ path: out, omitBackground: true, clip: box });
await browser.close();
console.log("wrote", out, box.width + "x" + box.height);
