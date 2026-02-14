#!/usr/bin/env node
/**
 * Blog graphic renderer — Auryth AI
 *
 * Renders HTML templates to PNG using Puppeteer.
 * Supports dark (default) and light theme variants.
 *
 * Usage:
 *   node render.mjs <input.html> <output.png> [--width 1200] [--scale 2] [--theme dark|light]
 *
 * Or programmatically:
 *   import { renderGraphic } from './render.mjs'
 *   await renderGraphic('input.html', 'output.png', { width: 1200, scale: 2, theme: 'dark' })
 */

import puppeteer from "puppeteer";
import { readFileSync, mkdirSync } from "fs";
import { dirname, resolve } from "path";

/**
 * Render an HTML file to PNG.
 * @param {string} inputPath  - Path to HTML file
 * @param {string} outputPath - Path for output PNG
 * @param {object} opts       - { width?: number, scale?: number, theme?: 'dark'|'light' }
 */
export async function renderGraphic(inputPath, outputPath, opts = {}) {
  const { width = 1200, scale = 2, theme = "dark" } = opts;

  // Ensure output directory exists
  mkdirSync(dirname(resolve(outputPath)), { recursive: true });

  const browser = await puppeteer.launch({
    headless: "new",
    args: ["--no-sandbox", "--disable-setuid-sandbox"],
  });

  try {
    const page = await browser.newPage();
    await page.setViewport({ width, height: 800, deviceScaleFactor: scale });

    // Load HTML file
    let html = readFileSync(resolve(inputPath), "utf-8");

    // For light theme, add .light class to <body>
    if (theme === "light") {
      html = html.replace(/<body/, '<body class="light"');
    }

    await page.setContent(html, { waitUntil: "networkidle0" });

    // Auto-fit height to content
    const bodyHeight = await page.evaluate(
      () => document.body.scrollHeight
    );
    await page.setViewport({
      width,
      height: bodyHeight,
      deviceScaleFactor: scale,
    });

    // Screenshot the body
    await page.screenshot({
      path: resolve(outputPath),
      fullPage: true,
      omitBackground: false,
    });

    console.log(`✓ ${outputPath} (${width}x${bodyHeight} @${scale}x, ${theme})`);
  } finally {
    await browser.close();
  }
}

/**
 * Render a template with data injected.
 * Reads base.html, replaces {{CONTENT}} with the provided HTML string.
 *
 * @param {string} contentHtml - Inner HTML to inject
 * @param {string} outputPath  - Path for output PNG
 * @param {object} opts        - { width?: number, scale?: number, theme?: 'dark'|'light' }
 */
export async function renderTemplate(contentHtml, outputPath, opts = {}) {
  const baseDir = dirname(new URL(import.meta.url).pathname).replace(
    /^\//,
    ""
  );
  const basePath = resolve(baseDir, "templates", "base.html");
  const baseHtml = readFileSync(basePath, "utf-8");
  const fullHtml = baseHtml.replace("{{CONTENT}}", contentHtml);

  // Write temp file
  const tmpPath = resolve(baseDir, ".tmp-render.html");
  const { writeFileSync, unlinkSync } = await import("fs");
  writeFileSync(tmpPath, fullHtml);

  try {
    await renderGraphic(tmpPath, outputPath, opts);
  } finally {
    try {
      unlinkSync(tmpPath);
    } catch {}
  }
}

/**
 * Render both dark and light variants of an HTML file.
 * @param {string} inputPath  - Path to HTML file
 * @param {string} outputDir  - Directory for output PNGs
 * @param {string} baseName   - Base name for output files (without extension)
 * @param {object} opts       - { width?: number, scale?: number }
 */
export async function renderBothThemes(inputPath, outputDir, baseName, opts = {}) {
  await renderGraphic(inputPath, resolve(outputDir, `${baseName}-dark.png`), { ...opts, theme: "dark" });
  await renderGraphic(inputPath, resolve(outputDir, `${baseName}-light.png`), { ...opts, theme: "light" });
}

// ─── CLI ────────────────────────────────────────────────────────────
if (
  process.argv[1] &&
  (process.argv[1].endsWith("render.mjs") ||
    process.argv[1].endsWith("render"))
) {
  const args = process.argv.slice(2);
  const input = args[0];
  const output = args[1];

  if (!input || !output) {
    console.error("Usage: node render.mjs <input.html> <output.png> [--width 1200] [--scale 2] [--theme dark|light]");
    process.exit(1);
  }

  const widthIdx = args.indexOf("--width");
  const scaleIdx = args.indexOf("--scale");
  const themeIdx = args.indexOf("--theme");
  const width = widthIdx >= 0 ? parseInt(args[widthIdx + 1]) : 1200;
  const scale = scaleIdx >= 0 ? parseInt(args[scaleIdx + 1]) : 2;
  const theme = themeIdx >= 0 ? args[themeIdx + 1] : "dark";

  renderGraphic(input, output, { width, scale, theme }).catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
