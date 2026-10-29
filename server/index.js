import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer as createHttpServer, request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { extname, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
};

function sendJson(response, statusCode, body) {
  response.writeHead(statusCode, { 'content-type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(body));
}

function serveWeb(request, response, webDist) {
  if (!['GET', 'HEAD'].includes(request.method)) {
    sendJson(response, 405, { error: 'Method not allowed' });
    return;
  }

  const pathname = new URL(request.url, 'http://localhost').pathname;
  const candidate = resolve(webDist, `.${decodeURIComponent(pathname)}`);
  if (candidate !== webDist && !candidate.startsWith(`${webDist}${sep}`)) {
    sendJson(response, 400, { error: 'Invalid path' });
    return;
  }
  const file = existsSync(candidate) && statSync(candidate).isFile()
    ? candidate
    : resolve(webDist, 'index.html');
  if (!existsSync(file)) {
    sendJson(response, 503, { error: 'Web assets are unavailable. Run the frontend build first.' });
    return;
  }

  response.writeHead(200, { 'content-type': MIME_TYPES[extname(file)] || 'application/octet-stream' });
  if (request.method === 'HEAD') response.end();
  else createReadStream(file).pipe(response);
}

export function createAppServer({ fastApiUrl = 'http://127.0.0.1:8000', webDist = resolve(ROOT, 'web/dist') } = {}) {
  const upstream = new URL(fastApiUrl);
  return createHttpServer((request, response) => {
    if (request.url === '/healthz' && request.method === 'GET') {
      sendJson(response, 200, { status: 'ok', service: 'skillscope-web' });
      return;
    }

    if (request.url === '/api' || request.url.startsWith('/api/')) {
      const headers = { ...request.headers, host: upstream.host };
      delete headers.connection;
      const proxy = (upstream.protocol === 'https:' ? httpsRequest : httpRequest)({
        hostname: upstream.hostname,
        port: upstream.port || (upstream.protocol === 'https:' ? 443 : 80),
        protocol: upstream.protocol,
        method: request.method,
        path: request.url,
        headers,
      }, (upstreamResponse) => {
        response.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
        upstreamResponse.pipe(response);
      });
      proxy.on('error', () => {
        if (!response.headersSent) sendJson(response, 502, { detail: 'The FastAPI model service is unavailable.' });
        else response.destroy();
      });
      request.pipe(proxy);
      return;
    }

    serveWeb(request, response, webDist);
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 3000);
  const server = createAppServer({
    fastApiUrl: process.env.FASTAPI_URL || 'http://127.0.0.1:8000',
    webDist: resolve(process.env.WEB_DIST_DIR || resolve(ROOT, 'web/dist')),
  });
  server.listen(port, '0.0.0.0', () => console.log(`SkillScope web server listening on port ${port}`));
}
