#!/usr/bin/env node
/** Discover existing browser tools; never install packages or load credentials. */
import {
  existsSync,
  readdirSync,
  accessSync,
  constants,
  mkdirSync,
  realpathSync,
  readFileSync,
} from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repository = resolve(dirname(fileURLToPath(import.meta.url)), '../..');

function packageRoots() {
  const contractPath = join(repository, 'scripts/setup/cloud-contract.json');
  const projects = existsSync(contractPath)
    ? (JSON.parse(readFileSync(contractPath, 'utf8')).projects ?? [])
    : [];
  return [
    ...new Set([
      process.cwd(),
      repository,
      ...projects.map(project => resolve(repository, project.path)),
    ]),
  ];
}

export function findPlaywright(roots = packageRoots()) {
  const failures = [];
  for (const root of roots) {
    const require = createRequire(join(resolve(root), 'package.json'));
    for (const name of ['playwright', '@playwright/test', 'playwright-core']) {
      try {
        const modulePath = require.resolve(name);
        return { api: require(modulePath), modulePath };
      } catch (error) {
        if (error.code !== 'MODULE_NOT_FOUND') failures.push(`${name}: ${error.message}`);
      }
    }
    const store = join(root, 'node_modules/.pnpm');
    if (!existsSync(store)) continue;
    for (const entry of readdirSync(store).sort().reverse()) {
      if (!/^(playwright|playwright-core|@playwright\+test)@/.test(entry)) continue;
      for (const name of ['playwright', 'playwright-core', '@playwright/test']) {
        const candidate = join(store, entry, 'node_modules', name);
        try {
          const modulePath = require.resolve(candidate);
          return { api: require(modulePath), modulePath };
        } catch (error) {
          if (error.code !== 'MODULE_NOT_FOUND') failures.push(`${name}: ${error.message}`);
        }
      }
    }
  }
  throw new Error(
    `Playwright unavailable in current repository dependencies${failures.length ? `: ${failures.join('; ')}` : ''}`
  );
}

function executable(path) {
  try {
    accessSync(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

export function findBrowser(browserType, name, extraRoots = []) {
  if (process.env.CLOUD_BROWSER_EXECUTABLE) {
    const path = resolve(process.env.CLOUD_BROWSER_EXECUTABLE);
    if (!executable(path)) throw new Error('CLOUD_BROWSER_EXECUTABLE is not executable');
    return path;
  }
  const expected = browserType.executablePath();
  if (executable(expected)) return expected;
  const roots = [
    ...extraRoots,
    process.env.PLAYWRIGHT_BROWSERS_PATH,
    '/opt/pw-browsers',
    join(homedir(), '.cache/ms-playwright'),
    join(homedir(), 'Library/Caches/ms-playwright'),
  ].filter(Boolean);
  const names =
    name === 'chromium'
      ? ['chrome', 'chromium', 'headless_shell']
      : name === 'firefox'
        ? ['firefox']
        : ['pw_run.sh'];
  function search(root, depth) {
    if (!existsSync(root) || depth < 0) return undefined;
    for (const entry of readdirSync(root, { withFileTypes: true }).sort((a, b) =>
      b.name.localeCompare(a.name)
    )) {
      const path = join(root, entry.name);
      if (entry.isDirectory()) {
        const found = search(path, depth - 1);
        if (found) return found;
      } else if (names.includes(entry.name) && executable(path)) return path;
    }
  }
  for (const root of roots) {
    const found = search(root, 4);
    if (found) return found;
  }
  throw new Error(
    `${name} executable unavailable; expected ${expected}. No installation attempted.`
  );
}

export function localhostURL(value) {
  const url = new URL(value);
  if (
    !['http:', 'https:'].includes(url.protocol) ||
    !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) ||
    url.username ||
    url.password
  ) {
    throw new Error('render requires an HTTP localhost URL without credentials');
  }
  return url.href;
}

async function main(args) {
  const [command = 'doctor', value, output = '/tmp/cloud-browser.png'] = args;
  if (!['doctor', 'render'].includes(command))
    throw new Error(
      'Usage: node scripts/setup/cloud-browser.mjs doctor | render http://localhost:PORT/path /tmp/page.png'
    );
  const target = command === 'render' ? localhostURL(value) : undefined;
  const name = process.env.CLOUD_BROWSER || 'chromium';
  if (!['chromium', 'firefox', 'webkit'].includes(name))
    throw new Error('CLOUD_BROWSER must be chromium, firefox or webkit');
  const { api, modulePath } = findPlaywright();
  const executablePath = findBrowser(api[name], name);
  const capability = { browser: name, modulePath, executablePath };
  if (command === 'doctor') {
    console.log(
      JSON.stringify(
        { status: 'available', ...capability, launch: 'untested', application: 'untested' },
        null,
        2
      )
    );
    return;
  }
  const browser = await api[name].launch({ executablePath, headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const response = await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
    if (!response || !response.ok())
      throw new Error(`Local page returned ${response?.status() ?? 'no HTTP response'}`);
    // Local apps may request remote assets. This command does not change proxy settings.
    const screenshot = resolve(output);
    mkdirSync(dirname(screenshot), { recursive: true });
    await page.screenshot({ path: screenshot, fullPage: true });
    console.log(
      JSON.stringify(
        {
          status: 'rendered',
          ...capability,
          url: page.url(),
          httpStatus: response.status(),
          title: await page.title(),
          screenshot,
          application: 'untested: no control was driven',
        },
        null,
        2
      )
    );
  } finally {
    await browser.close();
  }
}

if (process.argv[1] && pathToFileURL(realpathSync(process.argv[1])).href === import.meta.url) {
  main(process.argv.slice(2)).catch(error => {
    console.error(
      JSON.stringify({
        status: 'unavailable',
        error: error.message.replace(/(https?:\/\/)[^\s/@]+:[^\s/@]+@/g, '$1[redacted]@'),
      })
    );
    process.exitCode = 2;
  });
}
