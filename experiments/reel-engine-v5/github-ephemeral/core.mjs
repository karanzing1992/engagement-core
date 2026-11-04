// Pure V5 GitHub ephemeral media contracts. No credentials, network or video data.
export const VERSION = "5.1.0-candidate";
export const CHUNK_LIMIT = 80 * 1024 * 1024;
export const MAX_SOURCE = 2 * 1024 * 1024 * 1024;
export const MAX_CHUNKS = 64;
export const DEFAULT_TTL_HOURS = 24;
export const ID_RE = /^[a-z][a-z0-9_-]{7,63}$/;
export const SHA_RE = /^[a-f0-9]{64}$/;
export const PROJECTS = new Set(["moksha_wellness","andaz_vibe_stay","delulutech","goa_community","synergistica"]);
const fail = message => { throw new Error(message); };
export function validateJob(data) {
  if (!data || typeof data !== "object" || Array.isArray(data)) fail("Job must be object");
  const {job_id, project_id, prompt, source_sha256, source_bytes, chunk_count, rights, verified_shots, verified_brand} = data;
  if (typeof job_id !== "string" || !ID_RE.test(job_id)) fail("Invalid job_id");
  if (!PROJECTS.has(project_id)) fail("Unregistered project");
  if (typeof prompt !== "string" || prompt.trim().length < 10 || prompt.length > 4000) fail("Creative prompt must be 10–4000 characters");
  if (typeof source_sha256 !== "string" || !SHA_RE.test(source_sha256)) fail("Source SHA-256 required");
  if (!Number.isSafeInteger(source_bytes) || source_bytes < 1024 || source_bytes > MAX_SOURCE) fail("Invalid source size");
  if (!Number.isSafeInteger(chunk_count) || chunk_count < 1 || chunk_count > MAX_CHUNKS || source_bytes > chunk_count * CHUNK_LIMIT || (chunk_count - 1) * CHUNK_LIMIT >= source_bytes) fail("Invalid chunk count");
  if (verified_shots !== undefined && (typeof verified_shots !== "object" || verified_shots === null || verified_shots.provenance !== "human_reviewed" || !Array.isArray(verified_shots.shots) || verified_shots.shots.length < 1 || verified_shots.shots.length > 1000)) fail("Human-reviewed shot metadata malformed");
  if (verified_brand !== undefined && (typeof verified_brand !== "string" || verified_brand.length < 25 || verified_brand.length > 8000)) fail("Invalid production brand context");
  if (!rights || rights.source_rights_confirmed !== true || rights.people_consent_confirmed !== true) fail("Explicit source and recognizable-person rights confirmations required");
  if (typeof rights.external_ai_processing_approved !== "boolean") fail("External model consent decision required");
  return {
    schema: 1, job_id, project_id, prompt: prompt.trim(),
    source_sha256, source_bytes, chunk_count,
    rights: {
      source_rights_confirmed: true,
      people_consent_confirmed: true,
      external_ai_processing_approved: rights.external_ai_processing_approved
    },
    ...(verified_shots === undefined ? {} : {verified_shots}),
    ...(verified_brand === undefined ? {} : {verified_brand}),
    state: "awaiting_upload", created_at: new Date().toISOString()
  };
}
export function jobTag(jobId) {
  if (!ID_RE.test(jobId)) fail("Invalid job identifier");
  return "mad-v5-tmp-" + jobId;
}
export function chunkAssetName(index) {
  if (!Number.isInteger(index) || index < 0 || index >= MAX_CHUNKS) fail("Invalid chunk index");
  return "source-" + String(index).padStart(3,"0") + ".part";
}
export function parseMetadata(release) {
  if (!release || release.draft !== true || typeof release.tag_name !== "string" ||
      !release.tag_name.startsWith("mad-v5-tmp-")) fail("Not an active temporary V5 release");
  let data;
  try { data = JSON.parse(release.body); } catch { fail("Invalid release metadata"); }
  if (!data || data.schema !== 1 || jobTag(data.job_id) !== release.tag_name) fail("Release metadata/tag mismatch");
  return data;
}
export function checkSourceAssets(data, assets) {
  const parts = (assets || []).filter(a => /^source-\d{3}\.part$/.test(a.name));
  if (parts.length !== data.chunk_count) fail("Incomplete source upload");
  let total = 0;
  for (let i=0;i<data.chunk_count;i++) {
    const name = chunkAssetName(i);
    const matches = parts.filter(a => a.name === name);
    if (matches.length !== 1 || !Number.isSafeInteger(matches[0].size) ||
        matches[0].size <= 0 || matches[0].size > CHUNK_LIMIT) fail("Invalid source chunk");
    total += matches[0].size;
  }
  if (total !== data.source_bytes) fail("Source byte count mismatch");
  return true;
}
export function validateChunkRequest(data, index, request) {
  if (data.state !== "awaiting_upload") fail("Upload window closed");
  if (!Number.isInteger(index) || index < 0 || index >= data.chunk_count) fail("Chunk not in manifest");
  const length = Number(request.headers.get("content-length"));
  if (!Number.isSafeInteger(length) || length < 1 || length > CHUNK_LIMIT) fail("Invalid chunk Content-Length");
  if (request.headers.get("content-type") !== "application/octet-stream") fail("Binary application/octet-stream required");
  return chunkAssetName(index);
}
export function expired(release, nowMs = Date.now(), hours = DEFAULT_TTL_HOURS) {
  const time = Date.parse(release.created_at);
  if (!Number.isFinite(time)) fail("Invalid release timestamp");
  return nowMs - time >= hours * 60 * 60 * 1000;
}
export function outputAssets(assets) {
  const mp4 = (assets || []).find(a => a.name === "v5-output.mp4");
  const receipt = (assets || []).find(a => a.name === "v5-receipt.json");
  return {ready: Boolean(mp4 && receipt), video_asset_id: mp4?.id || null, receipt_asset_id: receipt?.id || null};
}
