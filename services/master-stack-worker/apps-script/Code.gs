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

function runMasterStackSync() {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(10000)) {
    console.log('Skipped: an earlier sync is still running');
    return;
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
    for (const repo of REPOS) {
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
