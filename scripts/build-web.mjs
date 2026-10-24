// Assembles the deployable site in web/ (Vercel runs this; see vercel.json):
//   web/          the story page (story/)
//   web/app/      the interactive chart (site/)
//   web/data/     the JSON datasets (data/*.json)
// todd.sh serves it all under /triangle, with no trailing slash on the pages (/triangle, /triangle/app), so each
// page gets a <base> that makes its relative links resolve under that prefix. The source folders keep working
// as they are locally (python3 -m http.server, then /story/ and /site/).

import fs from "node:fs";
import path from "node:path";

const root = path.resolve(import.meta.dirname, "..");
const out = path.join(root, "web");
const PREFIX = "/triangle";

fs.rmSync(out, { recursive: true, force: true });
fs.cpSync(path.join(root, "story"), out, { recursive: true });
fs.cpSync(path.join(root, "site"), path.join(out, "app"), {
  recursive: true,
  filter: (src) => !src.endsWith("README.md"),
});
fs.mkdirSync(path.join(out, "data"));
for (const name of fs.readdirSync(path.join(root, "data"))) {
  if (name.endsWith(".json")) fs.copyFileSync(path.join(root, "data", name), path.join(out, "data", name));
}

/** Put a <base> first in <head>, so it governs every relative URL after it, and swap local links for deployed ones. */
function rewrite(file, base, swaps) {
  let html = fs.readFileSync(file, "utf8");
  if (!/<head>/i.test(html)) throw new Error(`${file}: no <head>`);
  html = html.replace(/<head>/i, `<head>\n<base href="${base}">`);
  for (const [from, to] of swaps) {
    if (!html.includes(from)) throw new Error(`${file}: expected ${from}`);
    html = html.replaceAll(from, to);
  }
  fs.writeFileSync(file, html);
}

rewrite(path.join(out, "index.html"), `${PREFIX}/`, [['href="../site/"', 'href="app"']]);
rewrite(path.join(out, "app", "index.html"), `${PREFIX}/app/`, [['href="../story/"', `href="${PREFIX}"`]]);

const count = (dir) => fs.readdirSync(dir, { recursive: true }).length;
console.log(`web/: ${count(out)} files (story, app, ${fs.readdirSync(path.join(out, "data")).length} datasets)`);
