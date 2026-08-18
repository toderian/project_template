#!/usr/bin/env node
import { createRequire } from 'node:module';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { homedir } from 'node:os';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';

const require = createRequire(import.meta.url);

const DEFAULT_CACHE = `${homedir()}/.cache/google-docs-refine-suite`;
const DEFAULT_PROFILE = `${process.env.GOOGLE_DOCS_REFINE_CACHE || DEFAULT_CACHE}/chrome-profile`;

function printHelp() {
  console.log(`Usage:
  google-docs-refine.sh --url DOC_URL --input FILE --prompt TEXT --output FILE
  google-docs-refine.sh --url DOC_URL --input - --prompt-file prompt.txt
  google-docs-refine.sh --url DOC_URL --no-stage --prompt "Formalize this."

Options:
  --url URL           Google Doc URL to use as the workbench. If omitted, opens docs.new.
  --input FILE        Text to stage. Use - for stdin.
  --text TEXT         Text to stage directly.
  --prompt TEXT       Refinement prompt to copy to the clipboard after staging.
  --prompt-file FILE  File containing the refinement prompt.
  --auto-refine MODE  Run Docs Gemini refine UI automatically. Modes:
                      more-formal, rephrase, shorten, elaborate, bulletise,
                      bulletize, summarise, summarize.
  --output FILE       Write extracted final text to FILE. Defaults to stdout.
  --profile DIR       Chrome persistent profile directory.
  --cdp-endpoint URL  Attach to an already-running Chrome DevTools endpoint.
  --no-stage          Open the doc and copy prompt, but do not replace document text.
  --no-extract        Do not extract final text after the manual rewrite step.
  --leave-clipboard   Leave final extracted text on the clipboard instead of restoring it.
  --no-chromium-sandbox
                      Disable Chrome sandboxing if sandboxed launch fails.
  --timeout MS        Navigation/editor timeout. Default: 90000.
  --headed false      Run headless. Default is visible headed browser.
  --help              Show this help.

Flow:
  1. Open the Google Doc in a persistent Chrome profile.
  2. Replace document text unless --no-stage is set.
  3. Copy the prompt to the clipboard when provided.
  4. Run Docs Gemini/refine UI automatically when --auto-refine is set.
     Otherwise wait while you run it manually.
  5. Copy all document text back to --output or stdout.`);
}

function parseArgs(argv) {
  const opts = {
    url: '',
    inputFile: '',
    text: '',
    prompt: '',
    promptFile: '',
    autoRefine: '',
    outputFile: '',
    profile: DEFAULT_PROFILE,
    cdpEndpoint: '',
    stage: true,
    extract: true,
    leaveClipboard: false,
    chromiumSandbox: true,
    timeout: 90000,
    headed: true,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    const next = () => {
      if (i + 1 >= argv.length) throw new Error(`Missing value for ${arg}`);
      i += 1;
      return argv[i];
    };

    if (arg === '--help' || arg === '-h') opts.help = true;
    else if (arg === '--url') opts.url = next();
    else if (arg === '--input') opts.inputFile = next();
    else if (arg === '--text') opts.text = next();
    else if (arg === '--prompt') opts.prompt = next();
    else if (arg === '--prompt-file') opts.promptFile = next();
    else if (arg === '--auto-refine') opts.autoRefine = next();
    else if (arg === '--output') opts.outputFile = next();
    else if (arg === '--profile') opts.profile = resolve(next());
    else if (arg === '--cdp-endpoint') opts.cdpEndpoint = next();
    else if (arg === '--no-stage') opts.stage = false;
    else if (arg === '--no-extract') opts.extract = false;
    else if (arg === '--leave-clipboard') opts.leaveClipboard = true;
    else if (arg === '--no-chromium-sandbox') opts.chromiumSandbox = false;
    else if (arg === '--timeout') opts.timeout = Number(next());
    else if (arg === '--headed') opts.headed = next() !== 'false';
    else throw new Error(`Unknown option: ${arg}`);
  }

  if (!Number.isFinite(opts.timeout) || opts.timeout <= 0) {
    throw new Error('--timeout must be a positive number');
  }
  if (opts.help) return opts;
  if (opts.stage && !opts.inputFile && !opts.text) {
    throw new Error('Provide --input, --text, or --no-stage');
  }
  if (opts.inputFile && opts.text) {
    throw new Error('Use either --input or --text, not both');
  }
  if (opts.prompt && opts.promptFile) {
    throw new Error('Use either --prompt or --prompt-file, not both');
  }
  return opts;
}

async function readAllStdin() {
  const chunks = [];
  for await (const chunk of process.stdin) chunks.push(Buffer.from(chunk));
  return Buffer.concat(chunks).toString('utf8');
}

async function readInputText(opts) {
  if (!opts.stage) return '';
  if (opts.text) return opts.text;
  if (opts.inputFile === '-') return readAllStdin();
  return readFileSync(opts.inputFile, 'utf8');
}

function readPrompt(opts) {
  if (opts.prompt) return opts.prompt;
  if (opts.promptFile) return readFileSync(opts.promptFile, 'utf8').trim();
  return '';
}

function chromeExecutable() {
  const candidates = [
    process.env.CHROME_PATH,
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ].filter(Boolean);
  return candidates.find((path) => existsSync(path));
}

function docIdFromUrl(url) {
  const match = url.match(/\/document\/d\/([^/]+)/);
  return match ? match[1] : '';
}

async function openDocPage(context, url, timeout) {
  const targetUrl = url || 'https://docs.new';
  const targetDocId = docIdFromUrl(targetUrl);

  for (const page of context.pages()) {
    if (targetDocId && page.url().includes(`/document/d/${targetDocId}`)) {
      await page.bringToFront();
      return page;
    }
  }

  const page = context.pages()[0] || await context.newPage();
  await page.goto(targetUrl, { waitUntil: 'domcontentloaded', timeout });
  await page.bringToFront();
  return page;
}

async function waitForDocsReady(page, timeout) {
  const selectors = [
    '.kix-appview-editor',
    '.kix-page',
    'div[role="textbox"]',
    'iframe.docs-texteventtarget-iframe',
  ];

  const start = Date.now();
  while (Date.now() - start < timeout) {
    for (const selector of selectors) {
      if (await page.locator(selector).count().catch(() => 0)) return;
    }
    if (/accounts\.google\.com/.test(page.url())) {
      await page.waitForTimeout(1000);
    } else {
      await page.waitForTimeout(500);
    }
  }
  throw new Error('Timed out waiting for Google Docs editor. If sign-in is required, complete it in the browser and rerun.');
}

async function grantClipboard(context, page) {
  const origin = new URL(page.url()).origin;
  await context.grantPermissions(['clipboard-read', 'clipboard-write'], { origin }).catch(() => {});
}

async function setClipboard(page, text) {
  await page.evaluate(async (value) => {
    await navigator.clipboard.writeText(value);
  }, text);
}

async function readClipboard(page) {
  return page.evaluate(async () => navigator.clipboard.readText());
}

async function focusEditor(page) {
  const candidates = [
    '.kix-appview-editor',
    '.kix-page',
    'div[role="textbox"]',
    'iframe.docs-texteventtarget-iframe',
  ];

  for (const selector of candidates) {
    const locator = page.locator(selector).first();
    if (await locator.count().catch(() => 0)) {
      await locator.click({ timeout: 5000 }).catch(() => {});
      await page.waitForTimeout(250);
      return;
    }
  }

  const viewport = page.viewportSize() || { width: 1280, height: 900 };
  await page.mouse.click(Math.floor(viewport.width / 2), Math.floor(viewport.height * 0.45));
  await page.waitForTimeout(250);
}

async function replaceDocumentText(page, text) {
  await setClipboard(page, text);
  await focusEditor(page);
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.waitForTimeout(100);
  await page.keyboard.press('Backspace');
  await page.waitForTimeout(100);
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+V' : 'Control+V');
  await page.waitForTimeout(1000);
}

async function extractDocumentText(page) {
  await focusEditor(page);
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.waitForTimeout(150);
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+C' : 'Control+C');
  await page.waitForTimeout(500);
  return readClipboard(page);
}

function refineMode(mode) {
  const normalized = mode.trim().toLowerCase();
  const modes = {
    'more-formal': { label: /More formal/i, more: true },
    formal: { label: /More formal/i, more: true },
    formalize: { label: /More formal/i, more: true },
    formalise: { label: /More formal/i, more: true },
    rephrase: { label: /Rephrase/i, more: false },
    shorten: { label: /Shorten/i, more: false },
    elaborate: { label: /Elaborate/i, more: true },
    bulletise: { label: /Bulletise/i, more: true },
    bulletize: { label: /Bulletise/i, more: true },
    summarise: { label: /Summarise/i, more: true },
    summarize: { label: /Summarise/i, more: true },
  };

  const selected = modes[normalized];
  if (!selected) {
    throw new Error(`Unsupported --auto-refine mode: ${mode}`);
  }
  return selected;
}

async function waitForBodyText(page, predicate, timeout, description) {
  const start = Date.now();
  let lastText = '';
  while (Date.now() - start < timeout) {
    const text = await page.locator('body').innerText().catch(() => '');
    lastText = text;
    if (predicate(text)) return text;
    await page.waitForTimeout(1000);
  }
  throw new Error(`Timed out waiting for ${description}. Last body text tail: ${lastText.slice(-500)}`);
}

async function runAutoRefine(page, mode, timeout) {
  const selected = refineMode(mode);
  await focusEditor(page);
  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+A' : 'Control+A');
  await page.waitForTimeout(300);

  await page.getByText('Gemini', { exact: true }).first().click({ timeout });
  await page.waitForTimeout(500);
  await page.getByText('Refine selected text', { exact: true }).click({ timeout });
  await page.waitForTimeout(800);

  if (selected.more) {
    await page.getByRole('button', { name: /More/ }).filter({ hasText: 'More' }).first().click({ timeout: 5000 });
    await page.waitForTimeout(800);
  }

  const item = selected.more
    ? page.getByRole('menuitem', { name: selected.label }).first()
    : page.getByText(selected.label).first();
  await item.click({ timeout, force: true });

  await waitForBodyText(
    page,
    (text) => /Accept/i.test(text) && !/Collecting|generating|Working|Loading/i.test(text),
    timeout,
    'Gemini refine suggestion',
  );

  const acceptCandidates = [
    page.getByRole('button', { name: /^Accept/i }).first(),
    page.locator('button:has-text("Accept")').first(),
    page.getByText('Accept', { exact: true }).last(),
  ];

  for (const candidate of acceptCandidates) {
    if (await candidate.count().catch(() => 0)) {
      await candidate.click({ timeout: 10000, force: true });
      await page.waitForTimeout(5000);
      return;
    }
  }

  await page.keyboard.press(process.platform === 'darwin' ? 'Meta+Enter' : 'Control+Enter');
  await page.waitForTimeout(5000);
}

async function waitForUser(prompt) {
  const rl = createInterface({ input, output });
  try {
    await rl.question(prompt);
  } finally {
    rl.close();
  }
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.help) {
    printHelp();
    return;
  }

  const { chromium } = require('playwright');
  const sourceText = await readInputText(opts);
  const prompt = readPrompt(opts);
  let browser = null;
  let context = null;
  let originalClipboard = null;
  let page = null;

  if (opts.cdpEndpoint) {
    browser = await chromium.connectOverCDP(opts.cdpEndpoint);
    context = browser.contexts()[0] || await browser.newContext();
  } else {
    mkdirSync(opts.profile, { recursive: true });
    const executablePath = chromeExecutable();
    const launchOptions = {
      headless: !opts.headed,
      executablePath,
      chromiumSandbox: opts.chromiumSandbox,
      viewport: { width: 1440, height: 1000 },
    };

    try {
      context = await chromium.launchPersistentContext(opts.profile, launchOptions);
    } catch (error) {
      if (!opts.chromiumSandbox || !/sandbox/i.test(error.message)) throw error;
      console.error('Chrome sandboxed launch failed; retrying with --no-chromium-sandbox.');
      context = await chromium.launchPersistentContext(opts.profile, {
        ...launchOptions,
        chromiumSandbox: false,
      });
    }
  }

  try {
    page = await openDocPage(context, opts.url, opts.timeout);
    await waitForDocsReady(page, opts.timeout);
    await grantClipboard(context, page);
    originalClipboard = await readClipboard(page).catch(() => null);

    if (opts.stage) {
      await replaceDocumentText(page, sourceText);
      console.error('Staged source text in the Google Doc.');
    }

    if (prompt) {
      await setClipboard(page, prompt);
      console.error('Copied refinement prompt to the clipboard.');
      console.error(`Prompt: ${prompt}`);
    }

    if (opts.autoRefine) {
      console.error(`Running Google Docs Gemini auto-refine mode: ${opts.autoRefine}`);
      await runAutoRefine(page, opts.autoRefine, opts.timeout);
      console.error('Accepted Google Docs Gemini refinement.');
    }

    if (opts.extract) {
      if (!opts.autoRefine) {
        await waitForUser('Run the Google Docs refinement UI, insert/replace the final text, then press Enter here to extract it. ');
      }
      let refined = '';
      try {
        refined = await extractDocumentText(page);
      } catch (error) {
        console.error(`Automatic clipboard extraction failed: ${error.message}`);
        await waitForUser('Click the document, press Ctrl+A then Ctrl+C in the browser, then press Enter here. ');
        refined = await readClipboard(page);
      }

      if (opts.outputFile) {
        mkdirSync(dirname(resolve(opts.outputFile)), { recursive: true });
        writeFileSync(opts.outputFile, refined, 'utf8');
        console.error(`Wrote refined text to ${opts.outputFile}`);
      } else {
        process.stdout.write(refined);
      }

      if (!opts.leaveClipboard && originalClipboard !== null) {
        await setClipboard(page, originalClipboard).catch(() => {});
      }
    } else {
      console.error('Leaving browser open for manual refinement.');
      await waitForUser('Press Enter to close the browser session. ');
    }
  } finally {
    if (opts.cdpEndpoint && browser) {
      await browser.disconnect();
    } else if (context) {
      await context.close();
    }
  }
}

main().catch((error) => {
  console.error(`error: ${error.message}`);
  process.exit(1);
});
