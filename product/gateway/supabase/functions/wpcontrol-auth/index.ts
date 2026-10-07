import 'jsr:@supabase/functions-js/edge-runtime.d.ts'

const CONSENT_URL = 'https://mokshagoa.com/wp-control/connect/'

Deno.serve((req) => {
  const url = new URL(req.url)
  const path = url.pathname.replace(/^\/(?:functions\/v1\/)?wpcontrol-auth/, '') || '/'

  if (req.method === 'GET' && path === '/health') {
    return Response.json({ ok: true, service: 'wpcontrol-auth', version: '0.2.0' })
  }

  if (req.method !== 'GET') {
    return Response.json({ ok: false, error: 'method_not_allowed' }, { status: 405 })
  }

  const target = new URL(CONSENT_URL)
  const allowed = ['authorization_id', 'code', 'error', 'error_code', 'error_description', 'state', 'type']
  for (const key of allowed) {
    const value = url.searchParams.get(key)
    if (value) target.searchParams.set(key, value)
  }

  return new Response(null, {
    status: 302,
    headers: {
      location: target.toString(),
      'cache-control': 'no-store',
      'referrer-policy': 'no-referrer',
      'x-content-type-options': 'nosniff',
    },
  })
})
