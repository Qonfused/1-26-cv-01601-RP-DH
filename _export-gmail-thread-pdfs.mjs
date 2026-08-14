#!/usr/bin/env node

import { mkdir, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const CDP_HTTP = process.env.GMAIL_CDP_HTTP || 'http://127.0.0.1:9222';
const REPOSITORY_ROOT = path.dirname(fileURLToPath(import.meta.url));
const OUTPUT_DIRECTORY = path.join(REPOSITORY_ROOT, 'Exhibits', 'Documents');

const THREADS = [
  //
  // Add Gmail threads to export here.
  //
  // Each thread should have an `id` (the Gmail thread ID), a `title` (used for
  // logging), and an `output` (the filename to save the PDF as). Optionally,
  // you can specify a `scale` factor for the PDF output.
  //
  // Example:
  // {
  //   id: '1914d0fedcab5f2d',
  //   title: 'Decision Update',
  //   output: 'Gmail - UT Admissions Decision Update - 2024-08-13.pdf',
  //   scale: 0.87,
  // },
  //
];

const delay = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

async function waitFor(callback, description, timeout = 20_000) {
  const deadline = Date.now() + timeout;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const value = await callback();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await delay(200);
  }
  throw new Error(`Timed out waiting for ${description}${lastError ? `: ${lastError.message}` : ''}`);
}

class CdpConnection {
  constructor(webSocketUrl) {
    this.webSocketUrl = webSocketUrl;
    this.nextId = 0;
    this.pending = new Map();
  }

  async open() {
    this.socket = new WebSocket(this.webSocketUrl);
    this.socket.onmessage = event => {
      const message = JSON.parse(event.data);
      if (!message.id || !this.pending.has(message.id)) return;
      const { resolve, reject } = this.pending.get(message.id);
      this.pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    };
    this.socket.onclose = () => {
      for (const { reject } of this.pending.values()) {
        reject(new Error('CDP target closed'));
      }
      this.pending.clear();
    };
    await new Promise((resolve, reject) => {
      this.socket.onopen = resolve;
      this.socket.onerror = reject;
    });
    return this;
  }

  send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.nextId;
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.close();
  }
}

async function targets() {
  const response = await fetch(`${CDP_HTTP}/json/list`);
  if (!response.ok) throw new Error(`CDP target request failed: ${response.status}`);
  return response.json();
}

async function cancelPrintPreview(target) {
  const connection = await new CdpConnection(target.webSocketDebuggerUrl).open();
  const expression = `(() => {
    let cancel;
    function visit(root) {
      for (const element of root.querySelectorAll('*')) {
        if (element.shadowRoot) visit(element.shadowRoot);
        if (element.tagName === 'CR-BUTTON' && element.textContent.trim() === 'Cancel') {
          cancel = element;
        }
      }
    }
    visit(document);
    if (!cancel) return false;
    cancel.click();
    return true;
  })()`;

  try {
    await Promise.race([
      waitFor(async () => {
        const result = await connection.send('Runtime.evaluate', {
          expression,
          returnByValue: true,
          userGesture: true,
        });
        return result.result.value;
      }, 'Chrome print-preview Cancel button', 8_000),
      delay(9_000),
    ]);
  } catch {
    // The target often closes before CDP returns the click result.
  } finally {
    connection.close();
  }
}

async function closeOldPrintArtifacts() {
  const openTargets = await targets();
  for (const target of openTargets.filter(item => item.url === 'chrome://print/')) {
    await cancelPrintPreview(target);
  }
  for (const target of (await targets()).filter(item => item.url.includes('view=pt'))) {
    await fetch(`${CDP_HTTP}/json/close/${target.id}`, { method: 'PUT' });
  }
  await waitFor(async () => {
    return !(await targets()).some(
      target => target.url === 'chrome://print/' || target.url.includes('view=pt'),
    );
  }, 'prior Gmail print targets to close', 8_000);
}

async function gmailTarget() {
  const existing = (await targets()).find(
    target => target.type === 'page'
      && target.url.startsWith('https://mail.google.com/')
      && !target.url.includes('view=pt'),
  );
  if (existing) return existing;

  const url = encodeURIComponent('https://mail.google.com/mail/u/0/#inbox');
  const response = await fetch(`${CDP_HTTP}/json/new?${url}`, { method: 'PUT' });
  if (!response.ok) throw new Error(`Could not open Gmail: ${response.status}`);
  return response.json();
}

async function exportThread(connection, thread) {
  await closeOldPrintArtifacts();
  const before = new Set((await targets()).map(target => target.id));

  await connection.send('Page.navigate', {
    url: `https://mail.google.com/mail/u/0/#all/${thread.id}`,
  });

  await waitFor(async () => {
    const result = await connection.send('Runtime.evaluate', {
      expression: `document.body.innerText.includes(${JSON.stringify(thread.title)})
        && Boolean(document.querySelector('button[aria-label="Print all"]'))`,
      returnByValue: true,
    });
    return result.result.value;
  }, `Gmail thread “${thread.title}”`);

  const clickResult = await connection.send('Runtime.evaluate', {
    expression: `(() => {
      const button = document.querySelector('button[aria-label="Print all"]');
      if (!button) return false;
      button.click();
      return true;
    })()`,
    returnByValue: true,
    userGesture: true,
  });
  if (!clickResult.result.value) throw new Error(`Print all was unavailable for “${thread.title}”`);

  const printSource = await waitFor(async () => {
    return (await targets()).find(
      target => !before.has(target.id) && target.type === 'page' && target.url.includes('view=pt'),
    );
  }, `Gmail print document for “${thread.title}”`);

  const preview = await waitFor(async () => {
    return (await targets()).find(
      target => !before.has(target.id) && target.type === 'page' && target.url === 'chrome://print/',
    );
  }, `Chrome print preview for “${thread.title}”`);
  await cancelPrintPreview(preview);

  const printConnection = await new CdpConnection(printSource.webSocketDebuggerUrl).open();
  try {
    await printConnection.send('Page.enable');
    await waitFor(async () => {
      const result = await printConnection.send('Runtime.evaluate', {
        expression: `document.readyState === 'complete' && document.title.startsWith('Gmail -')`,
        returnByValue: true,
      });
      return result.result.value;
    }, `completed Gmail print document for “${thread.title}”`);

    await Promise.race([
      printConnection.send('Runtime.evaluate', {
        expression: `Promise.all([
          document.fonts.ready,
          ...Array.from(document.images).map(image => image.complete
            ? Promise.resolve()
            : new Promise(resolve => {
                image.addEventListener('load', resolve, { once: true });
                image.addEventListener('error', resolve, { once: true });
              }))
        ])`,
        awaitPromise: true,
        returnByValue: true,
      }),
      delay(5_000),
    ]);

    const pdf = await printConnection.send('Page.printToPDF', {
      landscape: false,
      scale: thread.scale ?? 1,
      printBackground: true,
      displayHeaderFooter: false,
      paperWidth: 8.5,
      paperHeight: 11,
      marginTop: 0.4,
      marginBottom: 0.4,
      marginLeft: 0.4,
      marginRight: 0.4,
      preferCSSPageSize: false,
      generateTaggedPDF: true,
      generateDocumentOutline: true,
    });

    const bytes = Buffer.from(pdf.data, 'base64');
    if (bytes.length < 10_000 || !bytes.subarray(0, 5).equals(Buffer.from('%PDF-'))) {
      throw new Error(`Gmail returned an invalid PDF for “${thread.title}”`);
    }

    const outputPath = path.join(OUTPUT_DIRECTORY, thread.output);
    const temporaryPath = `${outputPath}.tmp`;
    await writeFile(temporaryPath, bytes);
    await rename(temporaryPath, outputPath);
    console.log(`${thread.title}: ${outputPath}`);
  } finally {
    printConnection.close();
    await fetch(`${CDP_HTTP}/json/close/${printSource.id}`, { method: 'PUT' }).catch(() => {});
  }
}

async function main() {
  await mkdir(OUTPUT_DIRECTORY, { recursive: true });

  let gmail;
  try {
    gmail = await gmailTarget();
  } catch (error) {
    throw new Error(
      `Chrome CDP is unavailable at ${CDP_HTTP}. Start the authenticated Chrome profile with `
      + '`--remote-debugging-port=9222` and run this script again.',
      { cause: error },
    );
  }

  const connection = await new CdpConnection(gmail.webSocketDebuggerUrl).open();
  try {
    await connection.send('Page.enable');
    for (const thread of THREADS) await exportThread(connection, thread);
  } finally {
    connection.close();
    await closeOldPrintArtifacts().catch(() => {});
  }
}

await main();
