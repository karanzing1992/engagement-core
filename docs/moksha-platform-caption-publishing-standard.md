# Moksha Social — platform-native caption and distribution standard
Status: source-verified operating guidance | 2026-10-12 | Owner: Moksha Social
Canonical Master: https://docs.google.com/document/d/1-dSumLKkhmpzqGF2P-4x5_ZNUh9JamH3ApfXv4y4EeM/edit

## Why this exists
An approved original Moksha Reel must be distributed with format-appropriate copy and metadata **for each authorized destination**, never a copied one-size-fits-all caption. Distinguish accepted/queued, actually published, failed, and manual-only. One network account is not blanket consent for publishing to a different brand/group.

## Master creative safeguards
- Preserve a single visual style, real official transparent-alpha logo, source provenance, rights and audio verification, 1080x1920 source where supported; brand captions for the *morning wellness knowledge series* are educational, without promotional calls-to-action or written brand-name repetition.
- Capture publish-ready media SHA and immutable rendition ID. Avoid duplicates; use a campaign key plus platform/destination/content hash. Retry only confirmed failures, never resend to a channel on uncertain timeout.
- Tag real collaborator accounts only if directly relevant, authorized, and verified on the exact social platform. Do **not** mass-tag unrelated influencers, creators or competitors for reach. A geolocation/keyword/hashtag is NOT the same as a clickable @mention. Use actual public accounts only, never infer an Instagram handle applies to LinkedIn or Pinterest.
- Respect content verification: natural daylight after waking may cue circadian timing; no assertion that a short sunlight ritual cures insomnia or disease; no aggressive barefoot/exposure instructions.
- Use https://mokshagoa.com when a trusted link is appropriate, but pure daily informational engagement posts do not need a sales link or CTA.

## Platform-by-platform guidance and approved channel route

| Platform / format | Recommended authored caption / discoverability | Limit / media check / owner |
| --- | --- | --- |
| Instagram Reels | Strong opening sentence, readable spaced paragraphs, ~3–5 accurate topic/location hashtags. Prefer no outbound link in feed caption. For this morning series avoid sales copy and fabricated @tags. | 9:16 H.264/AAC; 30-second approved original. Exact live requirements verified by provider at submission; Metricool `instagramData.type=REEL`, showReelOnFeed=true. |
| Facebook Reels | Conversational copy, short approachable steps, local context, ~2–3 relevant hashtags. | Metricool `facebookData.type=REEL`, video required. |
| YouTube Shorts | Search-intent title with a primary phrase; clear first description lines, distinctive description, relevant tags and #Shorts; declare general audience as not made for kids when appropriate. | Verified Shorts <=3 minutes for vertical video; title <=100 characters; description <=5000. `youtubeData.type=short`, set madeForKids accurately. |
| LinkedIn Page video | Workplace-wellbeing/professional context; a useful observation and takeaway, ~2–3 relevant hashtags. Do not tag members without contextual relevance. | Native video accepted; keep a concise professional caption. `linkedinData.type=post`. |
| Pinterest video Pin | Keyword-rich evergreen *title* and descriptive, save-worthy practical summary. Optional 2–3 specific hashtags, relevant destination URL. | Organic title <=100, description <=800; 9:16 1080x1920, 4 seconds to 5 minutes. Use exact verified pre-existing **Moksha** board (numeric ID `556335428908703013`), not invented board names. |
| Threads | Conversational, compact and authentic; fewer hashtags, no engagement-bait questions for this series. | Native video and distinct copy; `threadsData`. |
| Bluesky | One clear thought with a tiny amount of context and one or two topical hashtags. | <=300 characters; `blueskyData.postLanguages=['en']`. |
| X | Direct single-post message, single focal idea, 1–2 targeted hashtags; no artificial long thread. | Standard accounts often 280 characters, Premium varies; do not promise the max. `twitterData`. |
| Google Business Profile | Video in *media/gallery* and, when separately appropriate, a short local informative update. Do not stuff phone numbers/handles in GBP posts. | Google video <=30 seconds, <=75 MB, >=720p. Metricool `gmbData.type=photo` for media **has no caption**; optional separate `publication` carries text but not attached video. |
| Telegram channels/groups | Context-matched English/Russian; native @Moksha channel mentions only if verified, community-safe. Short practical copy with native video. | Telegram sendVideo caption <=1024 characters. Prefer first-party Engagement Core `POST /engagement-core/v1/telegram/publish` and read back `/telegram/status`; narrow to genuine Moksha-owned/relevant destinations (currently keys `primary`, `moksha`). Do not automatically include Andaz or Exclusiv even if enabled. |
| Snapchat Spotlight | Video first, very short description, optional #topic and relevant location. | 9:16 video, >=5 seconds; publish through actually authorized Snapchat native API/profile only. Existing plugin route is not proof of active OAuth. |
| VK Clips / page video | Natural **Russian-language** short guide and relevant Russian hashtags, no fabricated tagging. | Verify connected VK OAuth and target before posting; do not assume historical integration setup means active authorization. |
| WhatsApp Status / community | Human, short copy with video attached; no hashtags needed for discoverability. Do not send mass WhatsApp broadcast without correct permission and audience choice. | If no connected direct status publisher, prepare manual share copy/video; WACRM business review is separate from consumer WhatsApp Status. |
| TikTok | If account connected, native educational caption with specific short topical tags and sound permissions. | 9:16 video; `tiktokData`; no publishing if no account association. |

## Research references / live-source guardrails (checked 12 Oct 2026)
- Google Business Profile official gallery video limits: https://support.google.com/business/answer/6103862
- Google Business Profile posts vs video/updates: https://support.google.com/business/answer/7342169
- Pinterest organic video pins, title/description and safe areas: https://help.pinterest.com/en/article/review-pin-specs
- Pinterest board selection and video-post flow: https://help.pinterest.com/en/article/create-a-pin-from-an-image-or-video
- YouTube Shorts eligibility: https://support.google.com/youtube/answer/15424877
- YouTube title/description limits: https://support.google.com/youtube/answer/57407
- YouTube unique-description advice: https://support.google.com/youtube/answer/12948449
- LinkedIn Page native video constraints: https://www.linkedin.com/help/linkedin/answer/a1311816
- LinkedIn mentions notify specific people (avoid random tags): https://www.linkedin.com/help/linkedin/answer/a524212
- Telegram video caption technical cap: https://core.telegram.org/bots/api
- Snapchat Spotlight add description/location/#topic: https://help.snapchat.com/hc/en-us/articles/7012288096532-How-do-I-post-Snaps-to-Spotlight
- Metricool connector action contracts were introspected live on 12 Oct 2026; connector-asserted payload limits are provider behavior, not an official content policy. Do not confuse "scheduler accepted" with confirmed social live URL.

## Verified campaign behavior (12 Oct 2026)
- Approved source: `Morning_Light_Ritual_2026-10-12_MASTER_RERENDER_v4_1080x1920.mp4`, ~4.35 MB, H264/AAC 1080x1920 30fps 30.000s. No external photo licences were needed for this animation-only video; original music is part of this episode and must not be reused for future episodes.
- Google Drive source upload accepted: file ID `1htv6W6NYvJEH76oeBTIX-5fR01asFvVl`; a *private Drive preview URL* was rejected as source by Metricool. A short-lived authorized file-transfer URL successfully materialized media inside Metricool, resulting in its native static CDN video URL. Future workflow should prefer the already-uploaded Metricool-hosted media for the **same episode** only; never leak signed transfer URLs or classify this as a new permanently deployed upload gateway.
- The connected Metricool brand label is `moksha.goa` with timezone `Asia/Kolkata` and its platform-specific connected profiles. Actual scheduler accepted automatic posts for Instagram, Facebook, YouTube Shorts, LinkedIn, Threads, Bluesky, X, Pinterest (board Moksha), GBP video-gallery entry and GBP separate text update. Provider states were `PENDING` on 12 Oct before due times; these are *not* live delivery confirmation or permanent platform integration guarantees.
- Native WP Engagement Core Telegram `/telegram/status` returned 4 enabled destination entries and a historical 4-send receipt; `/vk/status` returned `connected=false`, `token_saved=false`. WPVibe Free plan then blocked subsequent requests until approximately 07:00 UTC 12 Oct. Telegram video for this campaign was **not sent** in that run; Snap OAuth couldn't be verified. Don't resend previous Telegram campaigns merely because statuses mention them. Manual WhatsApp Status is not an API-publish success.
- No publication to unrelated Andaz/Exclusiv Telegram groups. One channel per appropriate audience; no unrelated cross-venture content.

## Operator verification, compatibility and rollback
- Check the post list by the exact scheduled campaign date and provider. Preserve every provider post ID, scheduled time and final provider status. Keep a separate private campaign receipt in the Master registry, including manual handoffs.
- When the platform publishes, inspect final status and target permalink; don't claim a live post from pending state. If a scheduled task fails, inspect error and retry only that specific destination once fixed.
- This is **source policy and documented operational workflow**, not a new WordPress plugin release, Meta approval, credential, device bridge, or verified live auto-publishing service for Telegram/Snap/VK. To undo rule changes, revert this documentation commit. Do not delete already queued platform posts without explicit user authorization.
