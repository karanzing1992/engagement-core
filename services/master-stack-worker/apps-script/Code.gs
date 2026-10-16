/**
 * Moksha Master — Google Apps Script repository-to-Doc publisher.
 * Authorization: the owner's Google account (DocumentApp) plus optional
 * GitHub fine-grained PAT with read-only Contents on approved repositories.
 *
 * NO Supabase service_role key is required or allowed here.
 */
const MASTER_DOC_ID = '1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM';
const OWNER = 'karanzing1992';
const REPOS = [
  'moksha_wordpress', 'android_gpt_bridge', 'engagement-core',
  'mokshasitemap', 'andaz-vibe-stay', 'staycore-pms',
  'synergistica-website', 'constituency-ops-v1', 'gpt-pine-engineer'
];
const PER_REPO_LIMIT = 30;
const MAX_DOCUMENT_EVENTS_PER_CYCLE = 20;

function installMasterSyncTrigger() {
  const existing = ScriptApp.getProjectTriggers();
  existing.forEach(t => {
    if (t.getHandlerFunction() === 'runMasterStackSync') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('runMasterStackSync').timeBased().everyHours(1).create();
  console.log('Master stack hourly Google Apps Script sync installed');
}

function githubRead(path) {
  const token = PropertiesService.getScriptProperties().getProperty('GH_READ_TOKEN');
  const headers = {
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'Moksha-Master-Stack-Sync'
  };
  if (token) headers.Authorization = 'Bearer ' + token;
  const response = UrlFetchApp.fetch('https://api.github.com' + path, {
    method: 'get', headers, muteHttpExceptions: true
  });
  const status = response.getResponseCode();
  if (status !== 200) throw new Error('GitHub HTTP ' + status + ' for ' + path.split('?')[0]);
  return JSON.parse(response.getContentText());
}

function shortText(input, max) {
  return String(input || '').replace(/[\x00-\x1f]/g, ' ').replace(/\s+/g, ' ').slice(0, max);
}

function isMaterial(commit, detail) {
  const message = String(commit.commit && commit.commit.message || '');
  const touched = (detail.files || []).map(f => f.filename).filter(f =>
    !/(^|\/)(results|artifacts|screenshots)\//.test(f) &&
    !/\.github\/copilot-instructions\.md$/.test(f)
  );
  if (message.includes('STACK CHANGE')) return touched.length > 0;
  if (!/^(feat|fix|security|perf|refactor|release)(\(|:)|security|critical|migration|upgrade|capability/i.test(message)) return false;
  return touched.some(f =>
    /\.(php|tsx?|jsx?|py|json|toml|ya?ml)$/.test(f) ||
    /(^|\/)(src|includes|app|bridge|native_bridge|services|supabase|webhooks|wordpress)\//.test(f)
  );
}

function writeEvent(document, seen, repo, commit, detail) {
  const sha = commit.sha;
  const marker = '[MASTER-GITHUB-CHANGE:' + repo + ':' + sha + ']';
  if (seen.has(marker)) return false;
  const title = shortText((commit.commit && commit.commit.message || '').split('\n')[0], 160);
  const evidence = 'https://github.com/' + OWNER + '/' + repo + '/commit/' + sha;
  const paths = (detail.files || []).slice(0, 8).map(f => shortText(f.filename, 120)).join(', ');
  const body = document.getBody();
  body.appendParagraph(marker);
  body.appendParagraph('SOURCE DEVELOPMENT | ' + new Date().toISOString().slice(0, 10));
  body.appendParagraph('Project: ' + repo);
  body.appendParagraph('Change: ' + title);
  body.appendParagraph('Source: ' + evidence);
  body.appendParagraph('Affected files: ' + paths);
  body.appendParagraph('Status: Verified GitHub source change. Not proof of production deployment or approval.');
  body.appendParagraph('');
  seen.add(marker);
  return true;
}

// Existing hourly/manual entry point is retained only for migration and recovery.
// Demand-based updates use the signed Web App entry point below.
function runMasterStackSync() {
  return syncMasterRepos_(REPOS);
}

function runMasterStackSyncForRepo(repo) {
  if (!REPOS.includes(repo)) throw new Error('Repository not allowlisted');
  return syncMasterRepos_([repo]);
}

function syncMasterRepos_(selectedRepos) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    throw new Error('Master sync busy: retry the same signed event after the active run');
  }
  try {
    const props = PropertiesService.getScriptProperties();
    const doc = DocumentApp.openById(MASTER_DOC_ID);
    const current = doc.getBody().getText();
    const markers = new Set((current.match(/\[MASTER-GITHUB-CHANGE:[^\]]+\]/g) || []));
    let published = 0, scanned = 0;
    const issues = [];
    // Store cursor updates until the document has been saved AND read back.
    // Otherwise a failed document write could permanently skip source commits.
    const cursorUpdates = {};
    const appendedMarkers = [];
    for (const repo of selectedRepos) {
      if (published >= MAX_DOCUMENT_EVENTS_PER_CYCLE) break;
      const cursorKey = 'master_sha_' + repo.replace(/[^a-z0-9]/gi, '_');
      const previous = props.getProperty(cursorKey);
      try {
        const commits = githubRead('/repos/' + OWNER + '/' + repo + '/commits?per_page=' + PER_REPO_LIMIT);
        if (!Array.isArray(commits) || commits.length === 0) continue;
        if (!previous) {
          cursorUpdates[cursorKey] = commits[0].sha;
          console.log(repo + ' initialized cursor at ' + commits[0].sha.slice(0, 12));
          continue;
        }
        const index = commits.findIndex(c => c.sha === previous);
        if (index < 0) {
          issues.push(repo + ': cursor outside latest 30 commits; no cursor advancement');
          continue;
        }
        const changes = commits.slice(0, index).reverse();
        let finished = true;
        for (const commit of changes) {
          if (published >= MAX_DOCUMENT_EVENTS_PER_CYCLE) { finished = false; break; }
          const detail = githubRead('/repos/' + OWNER + '/' + repo + '/commits/' + commit.sha);
          scanned++;
          if (!isMaterial(commit, detail)) continue;
          if (writeEvent(doc, markers, repo, commit, detail)) {
            published++;
            appendedMarkers.push('[MASTER-GITHUB-CHANGE:' + repo + ':' + commit.sha + ']');
          }
        }
        // Persist only if all commits were inspected; prevents silent data loss.
        if (finished) cursorUpdates[cursorKey] = commits[0].sha;
      } catch (error) {
        issues.push(repo + ': ' + shortText(error.message, 160));
      }
    }
    // DocumentApp.flush() does not exist. Explicitly commit pending writes
    // before advancing any GitHub SHA checkpoint or declaring success.
    doc.saveAndClose();
    if (appendedMarkers.length) {
      const savedText = DocumentApp.openById(MASTER_DOC_ID).getBody().getText();
      const missing = appendedMarkers.filter(marker => !savedText.includes(marker));
      if (missing.length) {
        throw new Error('Master document save verification failed; cursors unchanged');
      }
    }
    if (Object.keys(cursorUpdates).length) {
      props.setProperties(cursorUpdates, false);
    }
    props.setProperty('master_last_success', new Date().toISOString());
    props.setProperty('master_last_count', String(published));
    console.log(JSON.stringify({scanned, published, issues}));
    return {scanned, published, issues};
  } finally {
    lock.releaseLock();
  }
}

function masterStackStatus() {
  const props = PropertiesService.getScriptProperties();
  return {
    lastSuccess: props.getProperty('master_last_success') || null,
    lastPublished: Number(props.getProperty('master_last_count') || 0),
    repoCount: REPOS.length,
    githubCredentialConfigured: !!props.getProperty('GH_READ_TOKEN'),
    triggerInstalled: ScriptApp.getProjectTriggers().some(t =>
      t.getHandlerFunction() === 'runMasterStackSync')
  };
}


// Demand-based signed event entry point. This must be installed in the OWNER's
// existing Apps Script Web App (execute-as-owner), not a duplicate publisher.
// Save MASTER_EVENT_HMAC_SECRET only in Script Properties; never in source,
// GitHub/Docs, URL query strings or runtime logs. Install as an authorized
// Web App with explicit access review; do not remove old trigger until tested.
function masterEventHex_(bytes) {
  return bytes.map(b => ('0' + (b & 255).toString(16)).slice(-2)).join('');
}
function masterConstantTimeEqual_(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  let diff = a.length ^ b.length;
  for (let i = 0; i < Math.max(a.length, b.length); i++) {
    diff |= (a.charCodeAt(i) || 0) ^ (b.charCodeAt(i) || 0);
  }
  return diff === 0;
}
function masterVerifyEvent_(event) {
  const props = PropertiesService.getScriptProperties();
  const secret = props.getProperty('MASTER_EVENT_HMAC_SECRET');
  if (!secret || secret.length < 32) throw new Error('Demand sync is not provisioned');
  if (!event || event.version !== 1 || event.kind !== 'github') throw new Error('Unsupported event');
  if (!REPOS.includes(event.repo) || !/^[a-f0-9]{40}$/.test(String(event.sha || ''))) {
    throw new Error('Unknown source');
  }
  const epoch = Number(event.timestamp);
  if (!Number.isSafeInteger(epoch) || Math.abs(Math.floor(Date.now()/1000) - epoch) > 300) {
    throw new Error('Expired event');
  }
  if (!/^[A-Za-z0-9_-]{12,80}$/.test(String(event.nonce || '')) ||
      !/^[a-f0-9]{64}$/.test(String(event.signature || ''))) {
    throw new Error('Invalid event signature');
  }
  const payload = [event.version,event.kind,event.repo,event.sha,event.timestamp,event.nonce].join('\n');
  const expected = masterEventHex_(Utilities.computeHmacSha256Signature(payload, secret));
  if (!masterConstantTimeEqual_(expected, event.signature)) throw new Error('Unauthenticated event');
}
function doPost(e) {
  try {
    // Do not log request bodies, signatures, tokens or private event metadata.
    const raw = e && e.postData && e.postData.contents;
    if (!raw || raw.length > 4096) throw new Error('Invalid request size');
    const event = JSON.parse(raw);
    masterVerifyEvent_(event);
    const marker = '[MASTER-GITHUB-CHANGE:' + event.repo + ':' + event.sha + ']';
    const before = DocumentApp.openById(MASTER_DOC_ID).getBody().getText();
    if (before.includes(marker)) {
      return ContentService.createTextOutput(JSON.stringify({ok:true,status:'already_published',marker}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    const result = runMasterStackSyncForRepo(event.repo);
    const verified = DocumentApp.openById(MASTER_DOC_ID).getBody().getText().includes(marker);
    return ContentService.createTextOutput(JSON.stringify({
      ok:verified, status:verified?'published':'not_published',
      marker, scanned:result.scanned, published:result.published, issues:result.issues
    })).setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      ok:false, status:'rejected_or_retryable', error:shortText(error.message,100)
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
