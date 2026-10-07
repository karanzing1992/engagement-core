import { McpServer } from 'npm:@modelcontextprotocol/sdk@1.25.3/server/mcp.js'
import { z } from 'npm:zod@4.1.13'
import {
  type UserContext,
  callWordPress,
  connectSite,
  failed,
  listSites,
  needAuth,
  toolPayload,
} from './core.ts'

const secured: any = [{ type: 'oauth2', scopes: ['email', 'offline_access'] }]
const siteId = z.string().uuid()

export function makeServer(ctx: UserContext) {
  const server = new McpServer(
    { name: 'wordpress-control', version: '0.2.0' },
    {
      instructions:
        'Manage only WordPress sites paired by the current user. ' +
        'Default new content to draft unless the user explicitly asks to publish. ' +
        'Never request WordPress passwords, database passwords or hosting credentials.',
    } as any,
  )

  server.registerTool(
    'get_profile',
    {
      title: 'Get WP Control profile',
      description: 'Show the connected WP Control account and number of paired WordPress sites.',
      inputSchema: {},
      securitySchemes: secured,
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      _meta: { 'openai/profile': true },
    } as any,
    async () => {
      if (!ctx) return needAuth()
      const sites = await listSites(ctx.id)
      return toolPayload(
        { user_id: ctx.id, email: ctx.email || null, sites: sites.length },
        (ctx.email || 'Connected account') + ' · ' + sites.length + ' site(s)',
      )
    },
  )

  server.registerTool(
    'list_sites',
    {
      title: 'List connected WordPress sites',
      description: 'List WordPress sites owned by the connected WP Control account.',
      inputSchema: {},
      securitySchemes: secured,
      annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
    } as any,
    async () => {
      if (!ctx) return needAuth()
      const sites = await listSites(ctx.id)
      return toolPayload(sites, 'Found ' + sites.length + ' connected WordPress site(s).')
    },
  )

  server.registerTool(
    'connect_site',
    {
      title: 'Connect a WordPress site',
      description:
        'Pair a self-hosted WordPress site using the short-lived code generated inside the WP Control WordPress plugin.',
      inputSchema: {
        site_url: z.string().url(),
        pairing_code: z.string().min(6).max(32),
      },
      securitySchemes: secured,
      annotations: { readOnlyHint: false, destructiveHint: false, openWorldHint: true },
    } as any,
    async ({ site_url, pairing_code }: any) => {
      if (!ctx) return needAuth()
      try {
        const site = await connectSite(ctx, site_url, pairing_code)
        return toolPayload(site, 'Connected ' + site.name + '.')
      } catch (error) {
        return failed(error, 'site_pairing_failed')
      }
    },
  )

  const readTool = (
    name: string,
    title: string,
    description: string,
    schema: Record<string, any>,
    action: string,
  ) => {
    server.registerTool(
      name,
      {
        title,
        description,
        inputSchema: { site_id: siteId, ...schema },
        securitySchemes: secured,
        annotations: { readOnlyHint: true, destructiveHint: false, openWorldHint: false },
      } as any,
      async ({ site_id, ...input }: any) => {
        if (!ctx) return needAuth()
        try {
          return toolPayload(await callWordPress(ctx, site_id, action, input, name))
        } catch (error) {
          return failed(error, name + '_failed')
        }
      },
    )
  }

  const writeTool = (
    name: string,
    title: string,
    description: string,
    schema: Record<string, any>,
    action: string,
    destructive = false,
    idempotent = true,
  ) => {
    server.registerTool(
      name,
      {
        title,
        description,
        inputSchema: { site_id: siteId, ...schema },
        securitySchemes: secured,
        annotations: {
          readOnlyHint: false,
          destructiveHint: destructive,
          idempotentHint: idempotent,
          openWorldHint: false,
        },
      } as any,
      async ({ site_id, ...input }: any) => {
        if (!ctx) return needAuth()
        try {
          if (action === 'flush_cache' || action === 'undo_change') input.confirm = true
          return toolPayload(await callWordPress(ctx, site_id, action, input, name))
        } catch (error) {
          return failed(error, name + '_failed')
        }
      },
    )
  }

  readTool(
    'site_overview',
    'Get WordPress site overview',
    'Get versions, theme, plugins and operational information for a connected WordPress site.',
    {},
    'site_overview',
  )

  readTool(
    'list_content',
    'List WordPress content',
    'List posts, pages or another post type with optional status and text filters.',
    {
      post_type: z.string().default('post'),
      status: z.string().default('any'),
      search: z.string().optional(),
      page: z.number().int().min(1).default(1),
      per_page: z.number().int().min(1).max(100).default(20),
    },
    'list_content',
  )

  readTool(
    'get_content',
    'Get WordPress content',
    'Read one WordPress post, page or custom post type by ID.',
    { post_id: z.number().int().positive() },
    'get_content',
  )

  writeTool(
    'create_content',
    'Create WordPress content',
    'Create a WordPress post or page. Status defaults to draft; use publish only when the user explicitly asks.',
    {
      title: z.string().min(1),
      content: z.string().optional(),
      excerpt: z.string().optional(),
      post_type: z.string().default('post'),
      status: z.enum(['draft', 'pending', 'private', 'publish']).default('draft'),
      slug: z.string().optional(),
    },
    'create_content',
    false,
    false,
  )

  writeTool(
    'update_content',
    'Update WordPress content',
    'Update selected fields on existing content. WordPress revisions and the undo journal preserve recoverability.',
    {
      post_id: z.number().int().positive(),
      title: z.string().optional(),
      content: z.string().optional(),
      excerpt: z.string().optional(),
      status: z.enum(['draft', 'pending', 'private', 'publish', 'future', 'trash']).optional(),
      slug: z.string().optional(),
      dry_run: z.boolean().optional(),
    },
    'update_content',
  )

  readTool(
    'list_products',
    'List WooCommerce products',
    'List products with optional status, search, category, SKU and pagination filters.',
    {
      status: z.string().default('any'),
      search: z.string().optional(),
      category: z.string().optional(),
      sku: z.string().optional(),
      page: z.number().int().min(1).default(1),
      per_page: z.number().int().min(1).max(100).default(20),
    },
    'list_products',
  )

  readTool(
    'get_product',
    'Get WooCommerce product',
    'Read full details for one WooCommerce product.',
    { product_id: z.number().int().positive() },
    'get_product',
  )

  writeTool(
    'update_product',
    'Update WooCommerce product',
    'Update selected product fields such as price, description, SKU or stock. Only supplied fields change.',
    {
      product_id: z.number().int().positive(),
      name: z.string().optional(),
      status: z.string().optional(),
      regular_price: z.string().optional(),
      sale_price: z.string().optional(),
      sku: z.string().optional(),
      description: z.string().optional(),
      short_description: z.string().optional(),
      manage_stock: z.boolean().optional(),
      stock_quantity: z.number().int().optional(),
      dry_run: z.boolean().optional(),
    },
    'update_product',
  )

  readTool(
    'list_orders',
    'List WooCommerce orders',
    'List orders with optional status, date, customer or text filters.',
    {
      status: z.string().default('any'),
      search: z.string().optional(),
      customer: z.number().int().positive().optional(),
      date_after: z.string().optional(),
      date_before: z.string().optional(),
      page: z.number().int().min(1).default(1),
      per_page: z.number().int().min(1).max(100).default(20),
    },
    'list_orders',
  )

  readTool(
    'get_order',
    'Get WooCommerce order',
    'Read full details for one WooCommerce order.',
    { order_id: z.number().int().positive() },
    'get_order',
  )

  writeTool(
    'add_order_note',
    'Add WooCommerce order note',
    'Add an internal or customer-visible note. Customer-visible notes can trigger WooCommerce notification behavior.',
    {
      order_id: z.number().int().positive(),
      note: z.string().min(1),
      is_customer: z.boolean().default(false),
      dry_run: z.boolean().optional(),
    },
    'add_order_note',
    false,
    false,
  )

  readTool(
    'seo_audit',
    'Audit WordPress SEO metadata',
    'Scan content for SEO metadata issues using the active supported SEO provider.',
    {
      post_type: z.array(z.string()).optional(),
      post_status: z.string().default('publish'),
      only_issues: z.boolean().default(true),
      page: z.number().int().min(1).default(1),
      per_page: z.number().int().min(1).max(100).default(50),
    },
    'seo_audit',
  )

  writeTool(
    'update_seo',
    'Update WordPress SEO metadata',
    'Update selected SEO fields using the active SEO provider. Empty strings clear field overrides.',
    {
      post_id: z.number().int().positive(),
      title: z.string().optional(),
      description: z.string().optional(),
      focus_keyword: z.string().optional(),
      canonical_url: z.string().optional(),
      noindex: z.boolean().optional(),
      nofollow: z.boolean().optional(),
      dry_run: z.boolean().optional(),
    },
    'update_seo',
  )

  writeTool(
    'flush_cache',
    'Flush WordPress cache',
    'Purge the active WordPress page cache for all content, the homepage, or one post.',
    {
      scope: z.enum(['all', 'home', 'post']).default('all'),
      post_id: z.number().int().positive().optional(),
      dry_run: z.boolean().optional(),
    },
    'flush_cache',
  )

  readTool(
    'list_changes',
    'List reversible WordPress changes',
    'List recent changes in the site undo journal before choosing one to undo.',
    {
      status: z.enum(['active', 'undone', 'not_undoable']).optional(),
      page: z.number().int().min(1).default(1),
      per_page: z.number().int().min(1).max(200).default(50),
    },
    'list_changes',
  )

  writeTool(
    'undo_change',
    'Undo a WordPress change',
    'Undo one specific journaled WordPress change by change ID.',
    {
      change_id: z.number().int().positive(),
      force: z.boolean().default(false),
      dry_run: z.boolean().optional(),
    },
    'undo_change',
    true,
    false,
  )


  readTool(
    'list_plugins',
    'List WordPress plugins',
    'List installed WordPress plugins with versions and active state using Engagement Core directly.',
    {},
    'plugin_list',
  )

  writeTool(
    'set_plugin_state',
    'Activate or deactivate WordPress plugin',
    'Activate or deactivate an installed plugin. Engagement Core and its control-path dependencies are protected from self-deactivation.',
    {
      plugin: z.string().min(1),
      action: z.enum(['activate', 'deactivate']),
    },
    'plugin_toggle',
    true,
    true,
  )

  readTool(
    'list_themes',
    'List WordPress themes',
    'List installed themes and identify the active theme.',
    {},
    'theme_list',
  )

  readTool(
    'get_site_options',
    'Read safe WordPress settings',
    'Read Engagement Core allowlisted WordPress and WooCommerce settings; secrets and arbitrary options are excluded.',
    {
      names: z.array(z.string()).optional(),
    },
    'options_get',
  )

  writeTool(
    'update_site_options',
    'Update safe WordPress settings',
    'Update only Engagement Core allowlisted WordPress and WooCommerce settings.',
    {
      values: z.record(z.any()),
    },
    'options_update',
  )

  readTool(
    'list_cron',
    'List WordPress scheduled jobs',
    'List scheduled WordPress cron hooks without exposing their raw arguments.',
    {
      limit: z.number().int().min(1).max(200).default(100),
    },
    'cron_list',
  )

  readTool(
    'query_wp_audit',
    'Query WP Control audit',
    'Read recent privacy-safe Engagement Core WP Control audit records.',
    {
      limit: z.number().int().min(1).max(100).default(50),
      ability: z.string().optional(),
      outcome: z.enum(['success', 'error']).optional(),
    },
    'audit_query',
  )

  readTool(
    'telegram_status',
    'Get Telegram publisher status',
    'Read the Engagement Core Telegram connection, enabled destinations and latest publish result.',
    {},
    'telegram_status',
  )

  writeTool(
    'telegram_publish',
    'Publish to Telegram',
    'Publish text and optional media through the Engagement Core Telegram bot integration. With no target filters it sends to all enabled destinations.',
    {
      text: z.string().optional(),
      media: z.array(z.object({
        type: z.enum(['photo', 'video', 'animation', 'audio', 'document']),
        url: z.string().url(),
        name: z.string().optional(),
      })).max(10).optional(),
      targets: z.array(z.string()).optional(),
      levels: z.array(z.string()).optional(),
      dry_run: z.boolean().optional(),
    },
    'telegram_publish',
    false,
    false,
  )

  return server
}
