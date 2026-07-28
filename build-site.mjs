import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";

const rootDir = resolve(".");
const sourceDir = resolve(rootDir, "site");
const outputDir = resolve(rootDir, "dist");

if (!existsSync(sourceDir)) {
  throw new Error("Missing site directory. Run the Python scan/dashboard generation first.");
}

rmSync(outputDir, { recursive: true, force: true });
mkdirSync(outputDir, { recursive: true });

cpSync(sourceDir, outputDir, { recursive: true });

console.log(`Copied static site from ${sourceDir} to ${outputDir}`);
