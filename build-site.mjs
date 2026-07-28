import { copyFileSync, cpSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const rootDir = resolve(".");
const sourceDir = resolve(rootDir, "site");
const outputDir = resolve(rootDir, "dist");
const clientDir = resolve(outputDir, "client");
const serverDir = resolve(outputDir, "server");
const hostingSource = resolve(rootDir, ".openai", "hosting.json");
const hostingOutputDir = resolve(outputDir, ".openai");
const serverEntry = resolve(serverDir, "index.js");

if (!existsSync(sourceDir)) {
  throw new Error("Missing site directory. Run the Python scan/dashboard generation first.");
}

rmSync(outputDir, { recursive: true, force: true });
mkdirSync(clientDir, { recursive: true });
mkdirSync(serverDir, { recursive: true });
mkdirSync(hostingOutputDir, { recursive: true });

cpSync(sourceDir, clientDir, { recursive: true });

if (existsSync(hostingSource)) {
  copyFileSync(hostingSource, resolve(hostingOutputDir, "hosting.json"));
}

const indexHtml = readFileSync(resolve(sourceDir, "index.html"), "utf-8");
const dashboardData = readFileSync(resolve(sourceDir, "dashboard-data.json"), "utf-8");

writeFileSync(
  serverEntry,
  `const INDEX_HTML = ${JSON.stringify(indexHtml)};
const DASHBOARD_JSON = ${JSON.stringify(dashboardData)};
const JSON_HEADERS = { "content-type": "application/json; charset=utf-8" };
const HTML_HEADERS = { "content-type": "text/html; charset=utf-8" };

export default {
  async fetch(request) {
    const requestUrl = new URL(request.url);
    const pathname = decodeURIComponent(requestUrl.pathname);

    if (pathname === "/dashboard-data.json") {
      return new Response(DASHBOARD_JSON, {
        status: 200,
        headers: JSON_HEADERS
      });
    }

    return new Response(INDEX_HTML, {
      status: 200,
      headers: HTML_HEADERS
    });
  }
};
`,
  "utf-8"
);

console.log(`Built deployment output in ${outputDir}`);
