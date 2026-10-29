import assert from 'node:assert/strict';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { createServer as createHttpServer } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { after, before, test } from 'node:test';
import { createAppServer } from './index.js';

let upstream;
let app;
let upstreamUrl;
let webDist;
let tempDir;
let appUrl;

before(async () => {
  tempDir = await mkdtemp(join(tmpdir(), 'skillscope-node-'));
  webDist = join(tempDir, 'dist');
  await mkdir(webDist);
  await writeFile(join(webDist, 'index.html'), '<main>SkillScope web</main>');
  await writeFile(join(webDist, 'asset.js'), 'export const ready = true;');

  upstream = createHttpServer((request, response) => {
    const chunks = [];
    request.on('data', (chunk) => chunks.push(chunk));
    request.on('end', () => {
      response.writeHead(request.url === '/api/fail' ? 422 : 200, { 'content-type': 'application/json' });
      response.end(JSON.stringify({ method: request.method, url: request.url, contentType: request.headers['content-type'], body: Buffer.concat(chunks).toString() }));
    });
  });
  await new Promise((resolve) => upstream.listen(0, '127.0.0.1', resolve));
  upstreamUrl = `http://127.0.0.1:${upstream.address().port}`;
  app = createAppServer({ fastApiUrl: upstreamUrl, webDist });
  await new Promise((resolve) => app.listen(0, '127.0.0.1', resolve));
  appUrl = `http://127.0.0.1:${app.address().port}`;
});

after(async () => {
  await Promise.all([app, upstream].map((server) => new Promise((resolve) => server.close(resolve))));
  await rm(tempDir, { recursive: true, force: true });
});

test('serves the React entry point and static assets', async () => {
  const page = await fetch(`${appUrl}/explore/jobs`);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /SkillScope web/);
  const asset = await fetch(`${appUrl}/asset.js`);
  assert.equal(await asset.text(), 'export const ready = true;');
});

test('forwards API method, path, query, and multipart body unchanged', async () => {
  const form = new FormData();
  form.append('job_title', 'Data Scientist');
  const response = await fetch(`${appUrl}/api/analyze?source=web`, { method: 'POST', body: form });
  const result = await response.json();
  assert.equal(result.method, 'POST');
  assert.equal(result.url, '/api/analyze?source=web');
  assert.match(result.body, /Data Scientist/);
  assert.match(result.contentType, /multipart\/form-data/);
});

test('preserves upstream API status and has a local health endpoint', async () => {
  assert.equal((await fetch(`${appUrl}/api/fail`)).status, 422);
  const health = await fetch(`${appUrl}/healthz`);
  assert.deepEqual(await health.json(), { status: 'ok', service: 'skillscope-web' });
});
