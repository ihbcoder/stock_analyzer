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
  `import http from "node:http";

const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || "0.0.0.0";
const INDEX_HTML = ${JSON.stringify(indexHtml)};
const DASHBOARD_JSON = ${JSON.stringify(dashboardData)};

const server = http.createServer((request, response) => {
  const requestUrl = new URL(request.url || "/", "http://localhost");
  const pathname = decodeURIComponent(requestUrl.pathname);

  if (pathname === "/dashboard-data.json") {
    response.writeHead(200, { "Content-Type": "application/json; charset=utf-8" });
    response.end(DASHBOARD_JSON);
    return;
  }

  response.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
  response.end(INDEX_HTML);
});

server.listen(port, host, () => {
  console.log(\`Stock Analyzer dashboard server listening on \${host}:\${port}\`);
});
`,
  "utf-8"
);

console.log(`Built deployment output in ${outputDir}`);
