import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

import { WebStandardStreamableHTTPServerTransport } from 'npm:@modelcontextprotocol/sdk@1.25.3/server/webStandardStreamableHttp.js'
import { authenticate, gatewayConstants, jsonResponse } from './lib/core.ts'
import { makeServer } from './lib/server.ts'

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const path = url.pathname.replace(/^\/(?:functions\/v1\/)?wpcontrol-mcp/, '') || '/'
  const cfg = gatewayConstants()

  if (req.method === 'GET' && path === '/health') {
    return jsonResponse({ ok: true, service: 'wordpress-control', version: '0.1.0' })
  }

  if (req.method === 'GET' && path === '/.well-known/oauth-protected-resource') {
    return jsonResponse({
      resource: cfg.mcpUrl,
      authorization_servers: [cfg.authIssuer],
      scopes_supported: cfg.scopes,
      bearer_methods_supported: ['header'],
    })
  }

  if (path !== '/mcp') {
    return jsonResponse({ ok: false, error: 'not_found' }, 404)
  }

  const ctx = await authenticate(req)
  const server = makeServer(ctx)
  const transport = new WebStandardStreamableHTTPServerTransport()
  await server.connect(transport)
  try {
    return await transport.handleRequest(req)
  } finally {
    await server.close().catch(() => undefined)
  }
})
