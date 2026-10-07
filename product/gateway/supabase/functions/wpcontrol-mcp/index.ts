import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

import { WebStandardStreamableHTTPServerTransport } from 'npm:@modelcontextprotocol/sdk@1.25.3/server/webStandardStreamableHttp.js'
import { authenticate, gatewayConstants, jsonResponse } from './lib/core.ts'
import { makeServer } from './lib/server.ts'

const BROWSER_ORIGINS = new Set([
  'https://mokshagoa.com',
  'https://wp-control-auth-ui.vercel.app',
])

function corsHeaders(req: Request): HeadersInit {
  const origin = req.headers.get('origin') || ''
  if (!BROWSER_ORIGINS.has(origin)) return {}
  return {
    'access-control-allow-origin': origin,
    'access-control-allow-methods': 'GET, POST, OPTIONS',
    'access-control-allow-headers': 'authorization, content-type, accept',
    'access-control-max-age': '600',
    vary: 'Origin',
  }
}

function withCors(req: Request, response: Response): Response {
  const headers = new Headers(response.headers)
  for (const [key, value] of Object.entries(corsHeaders(req))) headers.set(key, String(value))
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers })
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { status: 204, headers: corsHeaders(req) })
  }

  const url = new URL(req.url)
  const path = url.pathname.replace(/^\/(?:functions\/v1\/)?wpcontrol-mcp/, '') || '/'
  const cfg = gatewayConstants()

  if (req.method === 'GET' && path === '/health') {
    return withCors(req, jsonResponse({ ok: true, service: 'wordpress-control', version: '0.1.1' }))
  }

  if (req.method === 'GET' && path === '/.well-known/oauth-protected-resource') {
    return withCors(req, jsonResponse({
      resource: cfg.mcpUrl,
      authorization_servers: [cfg.authIssuer],
      scopes_supported: cfg.scopes,
      bearer_methods_supported: ['header'],
    }))
  }

  if (path !== '/mcp') {
    return withCors(req, jsonResponse({ ok: false, error: 'not_found' }, 404))
  }

  const ctx = await authenticate(req)
  const server = makeServer(ctx)
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  })
  await server.connect(transport)
  try {
    return withCors(req, await transport.handleRequest(req))
  } finally {
    await server.close().catch(() => undefined)
  }
})
