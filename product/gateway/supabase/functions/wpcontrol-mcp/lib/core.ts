export type UserContext = { id: string; email?: string; token: string } | null
export type SiteRow = {
  id: string
  owner_id: string | null
  name: string
  base_url: string
  status: string
  plan: string
  capabilities: Record<string, unknown>
}

const SUPABASE_URL = Deno.env.get('SUPABASE_URL') || 'https://saczglesalubroyaucqe.supabase.co'
const ANON_KEY = Deno.env.get('SUPABASE_ANON_KEY') || ''
const SERVICE_KEY = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || ''
const BASE = SUPABASE_URL + '/functions/v1/wpcontrol-mcp'
const RESOURCE_METADATA = BASE + '/.well-known/oauth-protected-resource'

export function gatewayConstants() {
  return {
    supabaseUrl: SUPABASE_URL,
    mcpUrl: BASE + '/mcp',
    resourceMetadata: RESOURCE_METADATA,
    authIssuer: SUPABASE_URL + '/auth/v1',
    scopes: ['email', 'offline_access'],
  }
}

export function jsonResponse(data: unknown, status = 200, extra: HeadersInit = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', ...extra },
  })
}

export function toolPayload(data: unknown, summary?: string) {
  const text = summary || (typeof data === 'string' ? data : JSON.stringify(data).slice(0, 5000))
  return { structuredContent: { data }, content: [{ type: 'text' as const, text }] }
}

export function needAuth() {
  const description = 'Connect your WP Control account to continue.'
  const challenge =
    'Bearer resource_metadata="' + RESOURCE_METADATA +
    '", error="invalid_token", error_description="' + description + '"'
  return {
    content: [{ type: 'text' as const, text: description }],
    isError: true,
    _meta: { 'mcp/www_authenticate': [challenge] },
  }
}

export function failed(error: any, fallback: string) {
  return {
    ...toolPayload({ error: String(error?.code || fallback) }, error?.message || fallback),
    isError: true,
  }
}

export async function authenticate(req: Request): Promise<UserContext> {
  const header = req.headers.get('authorization') || ''
  const match = header.match(/^Bearer\s+(.+)$/i)
  if (!match) return null

  const token = match[1]
  const res = await fetch(SUPABASE_URL + '/auth/v1/user', {
    headers: { authorization: 'Bearer ' + token, apikey: ANON_KEY },
    redirect: 'manual',
  })
  if (!res.ok) return null

  const user = await res.json().catch(() => null)
  if (!user?.id) return null

  return {
    id: String(user.id),
    email: typeof user.email === 'string' ? user.email : undefined,
    token,
  }
}

async function db(path: string, init: RequestInit = {}) {
  if (!SERVICE_KEY) {
    throw Object.assign(new Error('Gateway is not configured.'), { code: 'gateway_not_configured' })
  }
  const headers = new Headers(init.headers)
  headers.set('apikey', SERVICE_KEY)
  headers.set('authorization', 'Bearer ' + SERVICE_KEY)
  headers.set('content-type', 'application/json')

  const res = await fetch(SUPABASE_URL + '/rest/v1/' + path, {
    ...init,
    headers,
    redirect: 'manual',
  })

  const text = await res.text()
  let body: any = null
  if (text) {
    try { body = JSON.parse(text) } catch { body = { message: text } }
  }

  if (!res.ok) {
    throw Object.assign(new Error(body?.message || body?.code || 'Database request failed.'), {
      code: body?.code || 'database_error',
    })
  }
  return body
}

export async function listSites(userId: string): Promise<SiteRow[]> {
  const path =
    'wpcontrol_sites?select=id,owner_id,name,base_url,status,plan,capabilities' +
    '&owner_id=eq.' + encodeURIComponent(userId) +
    '&status=eq.active&order=created_at.asc'
  return (await db(path)) as SiteRow[]
}

async function ownedSite(userId: string, siteId: string): Promise<SiteRow> {
  const path =
    'wpcontrol_sites?select=id,owner_id,name,base_url,status,plan,capabilities' +
    '&id=eq.' + encodeURIComponent(siteId) +
    '&owner_id=eq.' + encodeURIComponent(userId) +
    '&status=eq.active&limit=1'
  const rows = (await db(path)) as SiteRow[]
  if (!rows?.length) {
    throw Object.assign(new Error('Site not found or not owned by this account.'), { code: 'site_not_found' })
  }
  return rows[0]
}

async function audit(
  siteId: string | null,
  userId: string,
  toolName: string,
  success: boolean,
  durationMs: number,
  errorCode = '',
) {
  try {
    await db('wpcontrol_audit', {
      method: 'POST',
      headers: { Prefer: 'return=minimal' },
      body: JSON.stringify({
        site_id: siteId,
        actor_user_id: userId,
        tool_name: toolName,
        success,
        duration_ms: Math.max(0, Math.round(durationMs)),
        error_code: errorCode,
      }),
    })
  } catch {
    // Audit failure must not mask a completed WordPress operation.
  }
}

function isPrivateV4(ip: string) {
  const p = ip.split('.').map(Number)
  if (p.length !== 4 || p.some((n) => !Number.isInteger(n) || n < 0 || n > 255)) return false
  return p[0] === 0 || p[0] === 10 || p[0] === 127 ||
    (p[0] === 100 && p[1] >= 64 && p[1] <= 127) ||
    (p[0] === 169 && p[1] === 254) ||
    (p[0] === 172 && p[1] >= 16 && p[1] <= 31) ||
    (p[0] === 192 && p[1] === 168) ||
    p[0] >= 224
}

function isPrivateV6(ip: string) {
  const s = ip.toLowerCase()
  return s === '::' || s === '::1' || s.startsWith('fc') || s.startsWith('fd') || /^fe[89ab]/.test(s)
}

async function safeBase(raw: string) {
  const url = new URL(raw)
  if (url.protocol !== 'https:' || url.username || url.password || (url.port && url.port !== '443')) {
    throw Object.assign(new Error('WordPress site must use a public HTTPS origin.'), { code: 'invalid_site_url' })
  }
  url.pathname = '/'
  url.search = ''
  url.hash = ''
  const host = url.hostname.toLowerCase()

  if (host === 'localhost' || host.endsWith('.local') || host.endsWith('.localhost') || host.endsWith('.internal')) {
    throw Object.assign(new Error('Private hosts are not allowed.'), { code: 'private_site_url' })
  }
  if (isPrivateV4(host) || isPrivateV6(host)) {
    throw Object.assign(new Error('Private IP addresses are not allowed.'), { code: 'private_site_url' })
  }

  if (!/^\d+\.\d+\.\d+\.\d+$/.test(host) && !host.includes(':')) {
    const ips: string[] = []
    for (const type of ['A', 'AAAA']) {
      const response = await fetch(
        'https://dns.google/resolve?name=' + encodeURIComponent(host) + '&type=' + type,
        { headers: { accept: 'application/dns-json' }, redirect: 'manual' },
      )
      if (!response.ok) continue
      const body = await response.json().catch(() => ({}))
      for (const row of body.Answer || []) {
        if (typeof row?.data === 'string') ips.push(row.data)
      }
    }
    const resolved = ips.filter((v) => /^\d+\.\d+\.\d+\.\d+$/.test(v) || v.includes(':'))
    if (!resolved.length) {
      throw Object.assign(new Error('WordPress hostname did not resolve.'), { code: 'site_dns_failed' })
    }
    if (resolved.some((v) => isPrivateV4(v) || isPrivateV6(v))) {
      throw Object.assign(new Error('WordPress hostname resolves to a private address.'), { code: 'private_site_url' })
    }
  }
  return url
}

export async function connectSite(ctx: NonNullable<UserContext>, rawUrl: string, code: string) {
  const base = await safeBase(rawUrl)
  const endpoint = new URL('/wp-json/wp-control/v1/pair', base)
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ code, owner_id: ctx.id }),
    redirect: 'manual',
  })
  const body = await response.json().catch(() => ({}))

  if (!response.ok || !body?.ok || !body?.site_id) {
    throw Object.assign(new Error(body?.message || 'Site pairing failed.'), {
      code: body?.code || 'site_pairing_failed',
    })
  }

  const returned = await safeBase(String(body.base_url || base.origin))
  if (returned.origin !== base.origin) {
    throw Object.assign(new Error('Paired site returned a different origin.'), { code: 'site_origin_mismatch' })
  }

  const row = {
    id: String(body.site_id),
    owner_id: ctx.id,
    name: String(body.name || base.hostname),
    base_url: base.origin,
    status: 'active',
    capabilities: body.capabilities || { wordpress: true },
    updated_at: new Date().toISOString(),
  }

  const saved = await db('wpcontrol_sites?on_conflict=id', {
    method: 'POST',
    headers: { Prefer: 'resolution=merge-duplicates,return=representation' },
    body: JSON.stringify(row),
  })
  return Array.isArray(saved) && saved.length ? saved[0] : row
}

export async function callWordPress(
  ctx: NonNullable<UserContext>,
  siteId: string,
  action: string,
  input: Record<string, unknown>,
  toolName: string,
) {
  const started = performance.now()
  try {
    const site = await ownedSite(ctx.id, siteId)
    const base = await safeBase(site.base_url)
    const endpoint = new URL('/wp-json/wp-control/v1/bridge', base)

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        authorization: 'Bearer ' + ctx.token,
        'content-type': 'application/json',
      },
      body: JSON.stringify({ site_id: siteId, action, input }),
      redirect: 'manual',
    })
    const body = await response.json().catch(() => ({}))

    if (!response.ok || body?.code || body?.ok === false) {
      throw Object.assign(new Error(body?.message || 'WordPress action failed.'), {
        code: body?.code || 'wordpress_error',
      })
    }

    let result = body?.result ?? body

    // Normalize provider-specific WordPress shapes into the stable public
    // WP Control contract. Cowboy MCP uses an uppercase ID for created posts
    // and "entries" for its undo journal; clients should not have to know that.
    if (result && typeof result === 'object') {
      if (action === 'create_content') {
        const row = result as Record<string, any>
        const id = row.id ?? row.post_id ?? row.ID
        if (id != null) {
          if (row.id == null) row.id = Number(id)
          if (row.post_id == null) row.post_id = Number(id)
        }
      }
      if (action === 'list_changes') {
        const row = result as Record<string, any>
        if (Array.isArray(row.entries) && !Array.isArray(row.items)) {
          row.items = row.entries
        }
      }
    }

    await audit(siteId, ctx.id, toolName, true, performance.now() - started)
    return result
  } catch (error) {
    const code = String((error as any)?.code || 'gateway_error')
    await audit(siteId || null, ctx.id, toolName, false, performance.now() - started, code)
    throw error
  }
}
