import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

import { WebStandardStreamableHTTPServerTransport } from 'npm:@modelcontextprotocol/sdk@1.25.3/server/webStandardStreamableHttp.js'
import { authenticate, gatewayConstants, jsonResponse } from './lib/core.ts'
import { makeServer } from './lib/server.ts'

Deno.serve(async (req) => {
  const url = new URL(req.url)
  const path = url.pathname.replace(/^\/(?:functions\/v1\/)?wpcontrol-mcp/, '') || '/'
  const cfg = gatewayConstants()

  if (req.method === 'GET' && path === '/health') {
    return jsonResponse({ ok: true, service: 'wordpress-control', version: '0.1.1' })
  }

  // ChatGPT and other clients may look for discovery metadata relative to the
  // advertised MCP endpoint (/mcp), not only relative to the Edge Function.
  if (req.method === 'GET' &&
      (path === '/.well-known/oauth-protected-resource' ||
       path === '/mcp/.well-known/oauth-protected-resource')) {
    return jsonResponse({
      resource: cfg.mcpUrl,
      authorization_servers: [cfg.authIssuer],
      scopes_supported: cfg.scopes,
      bearer_methods_supported: ['header'],
    })
  }


  // Serve standard issuer metadata from Supabase Auth at the alternate
  // endpoint-relative paths used by ChatGPT's MCP OAuth discovery fallback.
  // Never mint tokens or alter the canonical issuer.
  if (req.method === 'GET' &&
      (path === '/mcp/.well-known/oauth-authorization-server' ||
       path === '/mcp/.well-known/openid-configuration')) {
    const discoveryUrl = path.endsWith('/oauth-authorization-server')
      ? cfg.supabaseUrl + '/.well-known/oauth-authorization-server/auth/v1'
      : cfg.supabaseUrl + '/auth/v1/.well-known/openid-configuration'
    const response = await fetch(discoveryUrl, { redirect: 'manual' })
    return new Response(await response.text(), {
      status: response.status,
      headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
    })
  }

  // Some ChatGPT discovery probes send a bodyless POST with Accept: */*.
  // Return the OAuth challenge rather than the SDK's 406, without affecting
  // valid MCP requests, authenticated clients, or normal tool operations.
  if (path === '/mcp' && req.method === 'POST' &&
      req.headers.get('content-length') === '0' &&
      !req.headers.has('authorization')) {
    return jsonResponse({ ok: false, error: 'authorization_required' }, 401, {
      'www-authenticate':
        'Bearer resource_metadata="' + cfg.resourceMetadata +
        '", scope="' + cfg.scopes.join(' ') + '"',
      'cache-control': 'no-store',
    })
  }

  if (path !== '/mcp') {
    return jsonResponse({ ok: false, error: 'not_found' }, 404)
  }

  const ctx = await authenticate(req)
  const server = makeServer(ctx)
  const transport = new WebStandardStreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  })
  await server.connect(transport)
  try {
    return await transport.handleRequest(req)
  } finally {
    await server.close().catch(() => undefined)
  }
})
