import { chromium } from "playwright";
const OUT = process.argv[2];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1680, height: 920 }, deviceScaleFactor: 1 });

async function go(url, w = 1800) {
  await page.goto("http://localhost:3000" + url, { waitUntil: "networkidle", timeout: 45000 });
  await page.waitForTimeout(w);
}
async function snap(sel, name, w = 600) {
  const el = page.locator(sel).first();
  if (await el.count()) {
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(w);
    await el.screenshot({ path: `${OUT}/a-${name}.png` });
  } else { console.log("MISSING " + name + " (" + sel + ")"); }
}

// LANDING — hero viewport + footer
await go("/");
await page.screenshot({ path: `${OUT}/a-landing-top.png` });
await snap("footer", "footer");

// RESIDENT
await go("/resident");
await snap("#parking", "resident-parking");
await snap("#community", "resident-community");

// RESIDENT with destination
await page.fill("input[aria-label='Where are you headed?']", "Indiranagar").catch(()=>{});
await page.waitForTimeout(900);
const sug = page.locator("#parking ul li button").first();
if (await sug.count()) { await sug.click(); await page.waitForTimeout(1200); }
await snap("#parking", "resident-dest");

// OFFICER
await go("/officer", 2500);
await snap("#command", "officer-command", 1200);
await snap("#where", "officer-map", 4500);
await snap("#plan", "officer-plan");
await snap("#proof", "officer-proof");
await snap("#reports", "officer-reports");

console.log("done");
await browser.close();
