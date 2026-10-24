import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { McpServer } from "npm:@modelcontextprotocol/sdk@1.25.3/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "npm:@modelcontextprotocol/sdk@1.25.3/server/webStandardStreamableHttp.js";
import { z } from "npm:zod@4.1.13";
import { createClient } from "npm:@supabase/supabase-js@2.58.0";

const SB_URL = Deno.env.get("SUPABASE_URL") || "https://saczglesalubroyaucqe.supabase.co";
const ANON = Deno.env.get("SUPABASE_ANON_KEY") || "";
const BASE = SB_URL + "/functions/v1/mission-control-mcp";
const RESOURCE = BASE + "/.well-known/oauth-protected-resource";
const SCOPES = ["email", "offline_access"];
const DASHBOARD = "https://mokshagoa.com/mission-control/";
const TBL = "mission_control_mcp_inbox_v1";
const STATUSES = ["Working", "Done", "On Ice", "Deprecated"];
const SECURED = [{ type: "oauth2", scopes: SCOPES }];
const te = new TextEncoder();
const td = new TextDecoder();
function encode64(bytes) {
  let chars = "";
  for (let i = 0; i < bytes.length; i += 8192) {
    chars += String.fromCharCode(...bytes.subarray(i, i + 8192));
  }
  return btoa(chars);
}
function decode64(str) {
  return Uint8Array.from(atob(str), c => c.charCodeAt(0));
}
async function vaultKey() {
  const secret = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!secret) throw new Error("encryption_not_configured");
  const ikm = await crypto.subtle.importKey("raw", te.encode(secret), "HKDF", false, ["deriveKey"]);
  return crypto.subtle.deriveKey({
    name: "HKDF", hash: "SHA-256",
    salt: te.encode("mission-control-mcp-inbox-v1"),
    info: te.encode("separate-owner-task-aes-gcm")
  }, ikm, { name: "AES-GCM", length: 256 }, false, ["encrypt", "decrypt"]);
}
function aad(ownerId, taskId) { return te.encode("mission-control-mcp:" + ownerId + ":" + taskId); }
async function encryptTask(ownerId, taskId, data) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const cipher = new Uint8Array(await crypto.subtle.encrypt({
    name: "AES-GCM", iv, additionalData: aad(ownerId, taskId)
  }, await vaultKey(), te.encode(JSON.stringify(data))));
  return { payload_iv: encode64(iv), payload_ciphertext: encode64(cipher), payload_version: 1 };
}
async function decryptTask(ownerId, row) {
  const raw = await crypto.subtle.decrypt({
    name: "AES-GCM", iv: decode64(row.payload_iv), additionalData: aad(ownerId, row.id)
  }, await vaultKey(), decode64(row.payload_ciphertext));
  return JSON.parse(td.decode(raw));
}


function json(value, status = 200, headers = {}) {
  return new Response(JSON.stringify(value), {
    status, headers: { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff", ...headers }
  });
}
function challenge(error = "invalid_token") {
  return json({ error, message: "Connect Mission Control with your approved Supabase account." }, 401, {
    "www-authenticate": 'Bearer resource_metadata="' + RESOURCE + '", scope="' + SCOPES.join(" ") + '"'
  });
}
function payload(data, summary) {
  return { structuredContent: { data }, content: [{ type: "text", text: summary || JSON.stringify(data).slice(0, 12000) }] };
}
function failed(code) {
  return { isError: true, content: [{ type: "text", text: code }], structuredContent: { error: code } };
}
function validChatLink(raw) {
  if (!raw) return "";
  try {
    const u = new URL(raw);
    if (u.protocol !== "https:" || u.hostname !== "chatgpt.com" || u.username || u.password || u.port) return null;
    if (!/^\/(?:c\/|g\/[A-Za-z0-9_-]+\/c\/)[A-Za-z0-9_-]{8,120}\/?$/.test(u.pathname)) return null;
    if (u.search || u.hash) return null;
    return u.href;
  } catch { return null; }
}
async function authenticate(req) {
  if (!ANON) return null;
  const token = (req.headers.get("authorization") || "").match(/^Bearer\s+(\S+)$/i)?.[1];
  if (!token || token.length > 8192) return null;
  let res;
  try {
    res = await fetch(SB_URL + "/auth/v1/user", {
      headers: { apikey: ANON, authorization: "Bearer " + token },
      redirect: "error", signal: AbortSignal.timeout(8000)
    });
  } catch { return null; }
  if (!res.ok) return null;
  const user = await res.json().catch(() => null);
  if (!user || !/^[0-9a-f-]{36}$/i.test(String(user.id || ""))) return null;
  return {
    id: String(user.id), email: String(user.email || ""),
    db: createClient(SB_URL, ANON, {
      auth: { persistSession: false, autoRefreshToken: false },
      global: { headers: { Authorization: "Bearer " + token } }
    })
  };
}
function makeServer(ctx) {
  const server = new McpServer(
    { name: "mission-control", version: "0.1.0" },
    { instructions: "Private owner task staging. Do not claim to read all ChatGPT chats. Never invent conversation links or completion receipts. WordPress/Telegram vault is the source of truth; staged items are not automatically synced." }
  );
  server.registerTool("mission_control_connection", {
    title: "Mission Control connection status",
    description: "Show verified Supabase login, dashboard link and precise sync limitations. Does not expose tasks.",
    inputSchema: {},
    securitySchemes: SECURED,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    _meta: { "openai/profile": true }
  }, async () => payload({
    authenticated: true, account: ctx.email, dashboard: DASHBOARD,
    task_store: "Supabase owner-scoped AES-GCM-encrypted staging inbox",
    canonical_store: "WordPress Telegram OTP vault",
    incoming_auto_sync: false, account_wide_chat_discovery: false
  }, "Connected as " + (ctx.email || "Supabase user") + ". Task staging is ready; WordPress import is not yet connected."));

  server.registerTool("mission_control_open_dashboard", {
    title: "Open Mission Control",
    description: "Return the existing private Mission Control dashboard URL and login guidance.",
    inputSchema: {},
    securitySchemes: SECURED,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true }
  }, async () => payload({ url: DASHBOARD, login: "Private Telegram OTP", data: "WordPress canonical vault" }, DASHBOARD));

  server.registerTool("mission_control_capture_task", {
    title: "Capture a task from this chat",
    description: "Stage a new task under a project and one of four statuses. Only supplied details are stored; this does not enumerate ChatGPT chats or sync into WordPress yet.",
    inputSchema: {
      project: z.string().trim().min(1).max(100).default("Unfiled Chats"),
      title: z.string().trim().min(1).max(180),
      chat_title: z.string().trim().max(180).default(""),
      chat_url: z.string().max(400).default(""),
      summary: z.string().max(1500).default(""),
      next_step: z.string().max(700).default(""),
      blocker: z.string().max(700).default(""),
      status: z.enum(STATUSES).default("Working")
    },
    securitySchemes: SECURED,
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false }
  }, async (arg) => {
    const link = validChatLink(arg.chat_url);
    if (link === null) return failed("chat_url_must_be_a_private_chatgpt_conversation_link");
    const id = crypto.randomUUID();
    const record = {
      project: arg.project, chat_title: arg.chat_title, chat_url: link,
      title: arg.title, summary: arg.summary, next_step: arg.next_step,
      blocker: arg.blocker, status: arg.status
    };
    let sealed;
    try { sealed = await encryptTask(ctx.id, id, record); }
    catch { return failed("encryption_unavailable"); }
    const row = {
      id, owner_id: ctx.id, project: "Encrypted", chat_title: "",
      chat_url: "", title: "Encrypted", summary: "", next_step: "",
      blocker: "", status: "Working", sync_state: "staged",
      source: "chatgpt-mcp", ...sealed
    };
    const { data, error } = await ctx.db.from(TBL).insert(row)
      .select("id,sync_state,created_at").single();
    if (error) return failed("task_capture_failed");
    return payload({ id: data.id, project: record.project, title: record.title, status: record.status, sync_state: data.sync_state, created_at: data.created_at, encrypted: true },
      "Task encrypted and staged: " + record.title + " [" + record.status + "]. WordPress import is pending.");
  });

  server.registerTool("mission_control_list_staged", {
    title: "List captured tasks",
    description: "List the current account's staged tasks, optionally filtering by status, project or title.",
    inputSchema: {
      status: z.enum(STATUSES).optional(),
      project: z.string().trim().max(100).optional(),
      title_contains: z.string().trim().max(100).optional(),
      limit: z.number().int().min(1).max(100).default(30)
    },
    securitySchemes: SECURED,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false }
  }, async (arg) => {
    const { data, error } = await ctx.db.from(TBL)
      .select("id,payload_iv,payload_ciphertext,sync_state,created_at,updated_at")
      .order("updated_at", { ascending: false }).limit(1000);
    if (error) return failed("task_list_failed");
    const items = [];
    try {
      for (const row of data || []) {
        const decrypted = await decryptTask(ctx.id, row);
        if (arg.status && decrypted.status !== arg.status) continue;
        if (arg.project && decrypted.project !== arg.project) continue;
        if (arg.title_contains && !decrypted.title.toLowerCase().includes(arg.title_contains.toLowerCase())) continue;
        items.push({ id: row.id, ...decrypted, sync_state: row.sync_state, created_at: row.created_at, updated_at: row.updated_at });
        if (items.length >= arg.limit) break;
      }
    } catch { return failed("task_decryption_unavailable"); }
    return payload({ items, count: items.length, encrypted_at_rest: true, scan_capped: (data || []).length === 1000, canonical_synced: false },
      "Found " + items.length + " encrypted staged task(s). WordPress vault remains separate.");
  });

  server.registerTool("mission_control_update_staged", {
    title: "Update a captured task",
    description: "Edit one task in the Supabase staging inbox. This does not modify the WordPress canonical vault.",
    inputSchema: {
      task_id: z.string().uuid(),
      title: z.string().trim().min(1).max(180).optional(),
      status: z.enum(STATUSES).optional(),
      next_step: z.string().max(700).optional(),
      blocker: z.string().max(700).optional(),
      summary: z.string().max(1500).optional()
    },
    securitySchemes: SECURED,
    annotations: { readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false }
  }, async (arg) => {
    const { data: existing, error: readError } = await ctx.db.from(TBL)
      .select("id,payload_iv,payload_ciphertext").eq("id", arg.task_id).maybeSingle();
    if (readError) return failed("task_read_failed");
    if (!existing) return failed("task_not_found_or_not_owned");
    let record;
    try { record = await decryptTask(ctx.id, existing); }
    catch { return failed("task_decryption_unavailable"); }
    let changes = 0;
    for (const key of ["title", "status", "next_step", "blocker", "summary"]) {
      if (Object.prototype.hasOwnProperty.call(arg, key)) { record[key] = arg[key]; changes++; }
    }
    if (!changes) return failed("no_fields_to_update");
    let sealed;
    try { sealed = await encryptTask(ctx.id, existing.id, record); }
    catch { return failed("encryption_unavailable"); }
    const { data, error } = await ctx.db.from(TBL)
      .update({ ...sealed, updated_at: new Date().toISOString() })
      .eq("id", arg.task_id).select("id,sync_state,updated_at").maybeSingle();
    if (error) return failed("task_update_failed");
    if (!data) return failed("task_not_found_or_not_owned");
    return payload({ id: data.id, project: record.project, title: record.title, status: record.status, sync_state: data.sync_state, updated_at: data.updated_at, encrypted: true },
      "Updated encrypted staged task: " + record.title + " [" + record.status + "].");
  });

  server.registerTool("mission_control_readiness", {
    title: "Verify Mission Control services",
    description: "Check the public WordPress and Supabase backup health probes. Does not read private vault contents.",
    inputSchema: {},
    securitySchemes: SECURED,
    annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: true }
  }, async () => {
    const targets = [
      ["wordpress", "https://mokshagoa.com/wp-json/mission-control/v1/health"],
      ["supabase_backup", SB_URL + "/functions/v1/mission-control-backup-v1/health"]
    ];
    const out = {};
    for (const [name, url] of targets) {
      try {
        const r = await fetch(url, { redirect: "error", signal: AbortSignal.timeout(7000) });
        const body = r.ok ? await r.json().catch(() => ({})) : {};
        out[name] = { online: r.ok && body.ok === true, http_status: r.status };
      } catch { out[name] = { online: false, http_status: null }; }
    }
    return payload({ services: out, plugin_authenticated: true, auto_sync: false }, "Service health checked. Automated WordPress ingestion is not enabled.");
  });

  return server;
}

Deno.serve(async (req) => {
  const url = new URL(req.url);
  const path = url.pathname.replace(/^\/(?:functions\/v1\/)?mission-control-mcp/, "") || "/";
  if (req.method === "GET" && path === "/health") {
    return json({ ok: true, service: "mission-control-mcp", version: "0.1.0", private_data: false });
  }
  if (req.method === "GET" && ["/.well-known/oauth-protected-resource", "/mcp/.well-known/oauth-protected-resource"].includes(path)) {
    return json({ resource: BASE + "/mcp", authorization_servers: [SB_URL + "/auth/v1"], scopes_supported: SCOPES, bearer_methods_supported: ["header"] });
  }
  if (req.method === "GET" && ["/mcp/.well-known/oauth-authorization-server", "/mcp/.well-known/openid-configuration"].includes(path)) {
    const target = path.endsWith("oauth-authorization-server") ?
      SB_URL + "/.well-known/oauth-authorization-server/auth/v1" :
      SB_URL + "/auth/v1/.well-known/openid-configuration";
    try {
      const r = await fetch(target, { redirect: "error", signal: AbortSignal.timeout(7000) });
      return new Response(await r.text(), { status: r.status, headers: { "content-type": "application/json", "cache-control": "no-store" } });
    } catch { return json({ error: "discovery_unavailable" }, 503); }
  }
  if (path !== "/mcp") return json({ error: "not_found" }, 404);
  if (req.method !== "POST" && req.method !== "GET" && req.method !== "DELETE") return json({ error: "method_not_allowed" }, 405);
  const ctx = await authenticate(req);
  if (!ctx) return challenge();
  const server = makeServer(ctx);
  const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
  await server.connect(transport);
  try { return await transport.handleRequest(req); }
  catch { return json({ error: "mcp_request_failed" }, 500); }
  finally { await server.close().catch(() => undefined); }
});