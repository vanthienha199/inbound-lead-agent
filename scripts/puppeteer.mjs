/* Resolves puppeteer from wherever it is installed. Set PUPPETEER_FROM to the
   package.json of a project that has it, or just run `npm i puppeteer` here. */
import { createRequire } from "node:module";

const from = process.env.PUPPETEER_FROM;
export default from ? createRequire(from)("puppeteer") : (await import("puppeteer")).default;
