#!/usr/bin/env node
// Dependency-free bundler: deploy ONLY the reviewed V5 private GitHub MCP source.
import {readFile, mkdir, writeFile} from "node:fs/promises";
import {createHash} from "node:crypto";
import {fileURLToPath} from "node:url";
import {dirname, join} from "node:path";
const root=dirname(fileURLToPath(import.meta.url));
const core=await readFile(join(root,"core.mjs"),"utf8");
const worker=await readFile(join(root,"worker.mjs"),"utf8");
if(!worker.startsWith('import {validateJob,jobTag,parseMetadata,checkSourceAssets,validateChunkRequest,outputAssets,expired} from "./core.mjs";')) throw new Error("Unexpected worker dependency. Audit before deploy.");
const local=core.replace(/\bexport (const|function)\b/g,"$1");
const module=worker.replace(/^import[^\n]+\n/,"");
const bundled="// Auto-bundled from first-party V5 modules; credentials provided ONLY by Cloudflare secrets.\n"+local+"\n"+module;
if(/\bimport\s+.+\s+from\s+/.test(bundled)||!bundled.includes("export default")) throw new Error("Unexpected dependency in Cloudflare build");
await mkdir(join(root,"dist"),{recursive:true});
await writeFile(join(root,"dist","main.mjs"),bundled);
console.log(JSON.stringify({status:"BUILT_CLOUDFLARE_V5_MCP",bytes:Buffer.byteLength(bundled),sha256:createHash("sha256").update(bundled).digest("hex"),has_secrets:false}));
