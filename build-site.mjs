import { copyFileSync, cpSync, existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
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

writeFileSync(
  serverEntry,
  `import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const port = Number(process.env.PORT || 3000);
const host = process.env.HOST || "0.0.0.0";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const clientDir = path.resolve(__dirname, "..", "client");

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon"
};

function sendFile(filePath, response) {
  const extension = path.extname(filePath).toLowerCase();
  const contentType = mimeTypes[extension] || "application/octet-stream";
  response.writeHead(200, { "Content-Type": contentType });
  fs.createReadStream(filePath).pipe(response);
}

const server = http.createServer((request, response) => {
  const requestUrl = new URL(request.url || "/", "http://localhost");
  const normalizedPath = decodeURIComponent(requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname);
  const candidatePath = path.resolve(clientDir, "." + normalizedPath);

  if (!candidatePath.startsWith(clientDir)) {
    response.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Forbidden");
    return;
  }

  if (fs.existsSync(candidatePath) && fs.statSync(candidatePath).isFile()) {
    sendFile(candidatePath, response);
    return;
  }

  const fallbackPath = path.resolve(clientDir, "index.html");
  if (fs.existsSync(fallbackPath)) {
    sendFile(fallbackPath, response);
    return;
  }

  response.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
  response.end("Not found");
});

server.listen(port, host, () => {
  console.log(\`Stock Analyzer dashboard server listening on \${host}:\${port}\`);
});
`,
  "utf-8"
);

console.log(`Built deployment output in ${outputDir}`);
