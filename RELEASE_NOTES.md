# Release notes

## 0.4.0 — 2026-09-27

### Catalog

- Add show_event sidecar and push_deliver run kind ([NEU-1480](https://linear.app/neuroticsasquatch/issue/NEU-1480)) ([#360](https://github.com/neuroticsasquat-ch/tvbf/pull/360))
- Detect premiere and ended/revived transitions in the delta ([NEU-1481](https://linear.app/neuroticsasquatch/issue/NEU-1481))

### General

- Use a rolling date for the "still anticipated" fixture in test_me_recommendations

### Push

- VAPID settings, key generation, public-key endpoint and push sender ([NEU-1484](https://linear.app/neuroticsasquatch/issue/NEU-1484)) ([#362](https://github.com/neuroticsasquat-ch/tvbf/pull/362))
- Push_subscription + push_delivery tables and /me/push/subscriptions ([NEU-1485](https://linear.app/neuroticsasquatch/issue/NEU-1485)) ([#363](https://github.com/neuroticsasquat-ch/tvbf/pull/363))
- POST /me/push/test sends a test push to one of my devices ([NEU-1486](https://linear.app/neuroticsasquatch/issue/NEU-1486)) ([#364](https://github.com/neuroticsasquat-ch/tvbf/pull/364))
- Notify_* preference flags, per-show mute, mute endpoint ([NEU-1490](https://linear.app/neuroticsasquatch/issue/NEU-1490)) ([#365](https://github.com/neuroticsasquat-ch/tvbf/pull/365))
- Notification candidates and payload builder ([NEU-1488](https://linear.app/neuroticsasquatch/issue/NEU-1488)) ([#366](https://github.com/neuroticsasquat-ch/tvbf/pull/366))
- Daily push delivery job with retirement and purge ([NEU-1489](https://linear.app/neuroticsasquatch/issue/NEU-1489)) ([#367](https://github.com/neuroticsasquat-ch/tvbf/pull/367))
- GET /admin/push/stats and push data in /me/export ([NEU-1493](https://linear.app/neuroticsasquatch/issue/NEU-1493)) ([#368](https://github.com/neuroticsasquat-ch/tvbf/pull/368))

## 0.3.4 — 2026-08-23

### General

- Add GET /users/{user_id}/feed endpoint for per-user activity feed
- Reorder InvalidCursor import to satisfy ruff

## 0.3.3 — 2026-08-23

### General

- Run recommendations on a model with capacity at payload size ([NEU-1180](https://linear.app/neuroticsasquatch/issue/NEU-1180))
- Fit the LLM timeout to the model the pass actually calls ([NEU-1180](https://linear.app/neuroticsasquatch/issue/NEU-1180))
- Serve in_my_shows from GET /shows and /shows/{id}/similar ([NEU-1185](https://linear.app/neuroticsasquatch/issue/NEU-1185))
- Serve my_rating on the watched-shows payload ([NEU-1191](https://linear.app/neuroticsasquatch/issue/NEU-1191))
- Anonymise display_name and auth_token in refresh_db.sh ([NEU-1195](https://linear.app/neuroticsasquatch/issue/NEU-1195))
- Anonymise even when pg_restore reports errors ([NEU-1195](https://linear.app/neuroticsasquatch/issue/NEU-1195))
- Make the restore-failure guidance mode-specific ([NEU-1195](https://linear.app/neuroticsasquatch/issue/NEU-1195))
- Reject an email-shaped display name at both write sites ([NEU-1194](https://linear.app/neuroticsasquatch/issue/NEU-1194))
- Verify Turnstile tokens and throttle auth by IP ([NEU-1160](https://linear.app/neuroticsasquatch/issue/NEU-1160))
- Require a verified email for connection requests and search visibility ([NEU-1161](https://linear.app/neuroticsasquatch/issue/NEU-1161))
- Disable an account and report a user ([NEU-1162](https://linear.app/neuroticsasquatch/issue/NEU-1162))
- Rate-limit outgoing connection requests ([NEU-1157](https://linear.app/neuroticsasquatch/issue/NEU-1157))
- Add admin read route for user reports ([NEU-1197](https://linear.app/neuroticsasquatch/issue/NEU-1197))
- Check local prerequisites and multiplex SSH in db:refresh
- Add app.user.handle with uniqueness, backfill and payload exposure ([NEU-1163](https://linear.app/neuroticsasquatch/issue/NEU-1163))
- Close the neutered backfill assertion and escape LIKE in handle search ([NEU-1163](https://linear.app/neuroticsasquatch/issue/NEU-1163))
- Drop app.watch_archive PII before open registration ([NEU-1158](https://linear.app/neuroticsasquatch/issue/NEU-1158))
- Add POST /contact endpoint with Turnstile, IP throttle, and email delivery ([NEU-1164](https://linear.app/neuroticsasquatch/issue/NEU-1164))
- Make invite_code optional in SignupRequest ([NEU-1165](https://linear.app/neuroticsasquatch/issue/NEU-1165))
- Raise CI flake threshold in burst acquisition test ([#332](https://github.com/neuroticsasquat-ch/tvbf/pull/332))

### Recommendations

- Demand a bare title and bump the prompt version
- Retry when most named titles resolve to nothing
- Stop serving the reason, keep writing it
- Name every excluded show in the payload
- Tell the model what to do instead of an excluded show
- Retry an answer that is all the user's own shows
- Recover the show title from a dressed answer ([NEU-1173](https://linear.app/neuroticsasquatch/issue/NEU-1173))
- Report recovered titles against what was named ([NEU-1173](https://linear.app/neuroticsasquatch/issue/NEU-1173))
- Suppress shows the viewer already has a record for ([NEU-1175](https://linear.app/neuroticsasquatch/issue/NEU-1175))
- Dismiss a show and never recommend it again ([NEU-1178](https://linear.app/neuroticsasquatch/issue/NEU-1178))

## 0.3.2 — 2026-08-16

### General

- Refresh catalog.show.popularity from the daily TMDB export ([NEU-1172](https://linear.app/neuroticsasquatch/issue/NEU-1172)) ([#293](https://github.com/neuroticsasquat-ch/tvbf/pull/293))
- Mirror TMDB recommendations and backfill the catalog ([NEU-1052](https://linear.app/neuroticsasquatch/issue/NEU-1052)) ([#294](https://github.com/neuroticsasquat-ch/tvbf/pull/294))
- Serve TMDB's similar shows at GET /shows/{id}/similar ([NEU-1053](https://linear.app/neuroticsasquatch/issue/NEU-1053)) ([#297](https://github.com/neuroticsasquat-ch/tvbf/pull/297))
- Capture a daily /trending/tv/week snapshot ([NEU-1055](https://linear.app/neuroticsasquatch/issue/NEU-1055)) ([#298](https://github.com/neuroticsasquat-ch/tvbf/pull/298))
- Serve the trending snapshot at GET /trending ([NEU-1056](https://linear.app/neuroticsasquatch/issue/NEU-1056)) ([#299](https://github.com/neuroticsasquat-ch/tvbf/pull/299))
- Most-anticipated query layer over catalog.show ([NEU-1058](https://linear.app/neuroticsasquatch/issue/NEU-1058)) ([#300](https://github.com/neuroticsasquat-ch/tvbf/pull/300))
- Serve the most-anticipated list at GET /anticipated ([NEU-1059](https://linear.app/neuroticsasquatch/issue/NEU-1059)) ([#301](https://github.com/neuroticsasquat-ch/tvbf/pull/301))

## 0.3.1 — 2026-08-16

### General

- Port a trimmed LLM client into src/tvbf/llm/ ([NEU-1098](https://linear.app/neuroticsasquatch/issue/NEU-1098)) ([#276](https://github.com/neuroticsasquat-ch/tvbf/pull/276))
- Register DeepInfra as a keyed source in the request budget ([NEU-1099](https://linear.app/neuroticsasquatch/issue/NEU-1099)) ([#277](https://github.com/neuroticsasquat-ch/tvbf/pull/277))
- Probe the DeepSeek model id and JSON mode against the live API ([NEU-1100](https://linear.app/neuroticsasquatch/issue/NEU-1100)) ([#278](https://github.com/neuroticsasquat-ch/tvbf/pull/278))
- Compute show completion percentage against aired episodes ([NEU-1102](https://linear.app/neuroticsasquatch/issue/NEU-1102)) ([#280](https://github.com/neuroticsasquat-ch/tvbf/pull/280))
- Classify each show as LIKED, NOT LIKED or INTERESTED ([NEU-1103](https://linear.app/neuroticsasquatch/issue/NEU-1103)) ([#281](https://github.com/neuroticsasquat-ch/tvbf/pull/281))
- Serialize the taste payload, hash it and gate on the weighted floor ([NEU-1104](https://linear.app/neuroticsasquatch/issue/NEU-1104)) ([#282](https://github.com/neuroticsasquat-ch/tvbf/pull/282))
- Print a user's compiled taste payload and token count as a dry run ([NEU-1105](https://linear.app/neuroticsasquatch/issue/NEU-1105)) ([#283](https://github.com/neuroticsasquat-ch/tvbf/pull/283))
- Add the recommendation set and recommendation tables ([NEU-1106](https://linear.app/neuroticsasquatch/issue/NEU-1106)) ([#284](https://github.com/neuroticsasquat-ch/tvbf/pull/284))
- Resolve a model-authored title and year to a catalog show ([NEU-1107](https://linear.app/neuroticsasquatch/issue/NEU-1107)) ([#285](https://github.com/neuroticsasquat-ch/tvbf/pull/285))
- Add the current-set repo function ([NEU-1108](https://linear.app/neuroticsasquatch/issue/NEU-1108)) ([#286](https://github.com/neuroticsasquat-ch/tvbf/pull/286))
- Build the weekly recommendations pass orchestrator ([NEU-1109](https://linear.app/neuroticsasquatch/issue/NEU-1109)) ([#287](https://github.com/neuroticsasquat-ch/tvbf/pull/287))
- Add POST /admin/recommendations with an optional user_id ([NEU-1110](https://linear.app/neuroticsasquatch/issue/NEU-1110)) ([#288](https://github.com/neuroticsasquat-ch/tvbf/pull/288))
- Give the weekly recommendations pass its own deadman ([NEU-1111](https://linear.app/neuroticsasquatch/issue/NEU-1111)) ([#289](https://github.com/neuroticsasquat-ch/tvbf/pull/289))
- Add GET /me/recommendations ([NEU-1112](https://linear.app/neuroticsasquatch/issue/NEU-1112)) ([#290](https://github.com/neuroticsasquat-ch/tvbf/pull/290))

## 0.3.0 — 2026-08-14

### Catalog

- Index the show->episode air FKs so cascaded deletes do not seq scan ([NEU-1066](https://linear.app/neuroticsasquatch/issue/NEU-1066))
- Repoint browse, search, /me and credits reads to catalog ([NEU-1047](https://linear.app/neuroticsasquatch/issue/NEU-1047))
- Backfill the credits the ingest mirrored before the writers existed ([NEU-1127](https://linear.app/neuroticsasquatch/issue/NEU-1127))
- Drop the tvmaze schema and relocate ingest_run ([NEU-1051](https://linear.app/neuroticsasquatch/issue/NEU-1051)) ([#252](https://github.com/neuroticsasquat-ch/tvbf/pull/252))
- Retire the TV Maze orphan rows from the catalog spine ([NEU-1146](https://linear.app/neuroticsasquatch/issue/NEU-1146))
- Keep specials out of the tier 2 season offset ([NEU-1146](https://linear.app/neuroticsasquatch/issue/NEU-1146))
- Separate proven from inferred de-duplications in the loss list ([NEU-1146](https://linear.app/neuroticsasquatch/issue/NEU-1146))

### General

- Run the daily update as a CLI entrypoint on a Coolify schedule ([NEU-1008](https://linear.app/neuroticsasquatch/issue/NEU-1008))
- Create the catalog schema and wire it through migrations, db:init and tests ([NEU-1026](https://linear.app/neuroticsasquatch/issue/NEU-1026))
- Create the catalog schema in CI too, the fifth hand-enumerated site ([NEU-1026](https://linear.app/neuroticsasquatch/issue/NEU-1026))
- Key request budgets by source and lease blocks ([NEU-1027](https://linear.app/neuroticsasquatch/issue/NEU-1027))
- Add the TMDB API client with bearer auth and a measured append cap ([NEU-1028](https://linear.app/neuroticsasquatch/issue/NEU-1028))
- Snapshot every watch and rating into app.watch_archive ([NEU-1029](https://linear.app/neuroticsasquatch/issue/NEU-1029))
- Add the per-user, per-show reconciliation harness ([NEU-1030](https://linear.app/neuroticsasquatch/issue/NEU-1030))
- Add catalog table definitions for the full TMDB surface ([NEU-1032](https://linear.app/neuroticsasquatch/issue/NEU-1032))
- Parse TMDB payloads and upsert them into catalog ([NEU-1033](https://linear.app/neuroticsasquatch/issue/NEU-1033))
- Copy tvmaze into catalog with ids preserved ([NEU-1042](https://linear.app/neuroticsasquatch/issue/NEU-1042))
- Map catalog rows onto tmdb_id in three tiers ([NEU-1043](https://linear.app/neuroticsasquatch/issue/NEU-1043))
- Mirror TMDB's whole catalog from the daily id export ([NEU-1034](https://linear.app/neuroticsasquatch/issue/NEU-1034))
- Size the catalog pass from measurement and split its failure counts ([NEU-1034](https://linear.app/neuroticsasquatch/issue/NEU-1034))
- Keep the catalog current with a daily /tv/changes delta ([NEU-1035](https://linear.app/neuroticsasquatch/issue/NEU-1035))
- Tombstone series absent from the TMDB id export ([NEU-1036](https://linear.app/neuroticsasquatch/issue/NEU-1036))
- Add catalog credit tables for person, character, cast and crew ([NEU-1038](https://linear.app/neuroticsasquatch/issue/NEU-1038))
- Apply pre-ship review findings on the catalog credit tables ([NEU-1038](https://linear.app/neuroticsasquatch/issue/NEU-1038))
- Apply pre-ship review findings on the episode credit writer ([NEU-1040](https://linear.app/neuroticsasquatch/issue/NEU-1040))
- Apply pre-ship review findings on the human matching queue ([NEU-1044](https://linear.app/neuroticsasquatch/issue/NEU-1044))
- Apply pre-ship review findings on the episode-grain mapping ([NEU-1045](https://linear.app/neuroticsasquatch/issue/NEU-1045))
- Compose TMDB image URLs in the API response ([NEU-1063](https://linear.app/neuroticsasquatch/issue/NEU-1063))
- Adopt TMDB's genre vocabulary verbatim at cutover ([NEU-1064](https://linear.app/neuroticsasquatch/issue/NEU-1064))
- Close the review gaps in the genre queries ([NEU-1064](https://linear.app/neuroticsasquatch/issue/NEU-1064))
- Add season_name to the friends feed payload ([NEU-1132](https://linear.app/neuroticsasquatch/issue/NEU-1132))
- Exclude special episodes from watch progress ([NEU-1062](https://linear.app/neuroticsasquatch/issue/NEU-1062))
- Un-marking a season must not skip copied specials ([NEU-1062](https://linear.app/neuroticsasquatch/issue/NEU-1062))
- Keep a special's feed event when its season or show is bulk-marked ([NEU-1062](https://linear.app/neuroticsasquatch/issue/NEU-1062))
- Correct mirrored airdates with a per-season offset ([NEU-1145](https://linear.app/neuroticsasquatch/issue/NEU-1145))
- Read the TV Maze lookup's id from its 301 Location header ([NEU-1145](https://linear.app/neuroticsasquatch/issue/NEU-1145))
- Cache the TV Maze show id so the airdate pass stops re-resolving it ([NEU-1148](https://linear.app/neuroticsasquatch/issue/NEU-1148))
- Correct the cached link's counters and its two dead-end paths ([NEU-1148](https://linear.app/neuroticsasquatch/issue/NEU-1148))
- Scope the nightly airdate work list to change ([NEU-1149](https://linear.app/neuroticsasquatch/issue/NEU-1149))

### Migration

- Add the human matching queue for unresolved user-touched shows ([NEU-1044](https://linear.app/neuroticsasquatch/issue/NEU-1044))
- Map the copied episode rows onto TMDB ids ([NEU-1045](https://linear.app/neuroticsasquatch/issue/NEU-1045))
- Deduplicate the season grain against the TMDB ingest ([NEU-1119](https://linear.app/neuroticsasquatch/issue/NEU-1119))
- Prune the unmatched copied shows the ingest duplicated ([NEU-1066](https://linear.app/neuroticsasquatch/issue/NEU-1066))
- Add the pre-cutover catalog coverage go/no-go gate ([NEU-1048](https://linear.app/neuroticsasquatch/issue/NEU-1048))
- Close the gate on unconfirmed tier-3 guesses ([NEU-1048](https://linear.app/neuroticsasquatch/issue/NEU-1048))
- Repoint the app foreign keys onto catalog ([NEU-1046](https://linear.app/neuroticsasquatch/issue/NEU-1046))
- Re-point user history onto the ingested episode rows ([NEU-1126](https://linear.app/neuroticsasquatch/issue/NEU-1126))

### Tmdb

- Mirror show cast and crew from aggregate_credits ([NEU-1039](https://linear.app/neuroticsasquatch/issue/NEU-1039))
- Mirror episode guest cast and crew from the season payload ([NEU-1040](https://linear.app/neuroticsasquatch/issue/NEU-1040))
- An episode credit with no person no longer fails the series payload ([NEU-1128](https://linear.app/neuroticsasquatch/issue/NEU-1128))

## 0.2.2 — 2026-08-07

### Scripts

- Band crew volume on tracked shows, not the whole catalogue ([#200](https://github.com/neuroticsasquat-ch/tvbf/pull/200))

### Tvmaze

- Tombstone shows deleted upstream ([NEU-1005](https://linear.app/neuroticsasquatch/issue/NEU-1005)) ([#201](https://github.com/neuroticsasquat-ch/tvbf/pull/201))
- Gone entities must not trip the consecutive-failure abort ([NEU-1006](https://linear.app/neuroticsasquatch/issue/NEU-1006)) ([#202](https://github.com/neuroticsasquat-ch/tvbf/pull/202))

## 0.2.1 — 2026-08-06

### Admin

- Reject concurrent runs of the same kind ([NEU-966](https://linear.app/neuroticsasquatch/issue/NEU-966)) ([#189](https://github.com/neuroticsasquat-ch/tvbf/pull/189))

### Browse

- Expose episode crew on the browse API ([NEU-963](https://linear.app/neuroticsasquatch/issue/NEU-963)) ([#193](https://github.com/neuroticsasquat-ch/tvbf/pull/193))

### Scripts

- Rate-base the episode-credits failure band and widen it

### Tvmaze

- Add episode credit table definitions and season watermark ([NEU-959](https://linear.app/neuroticsasquatch/issue/NEU-959)) ([#190](https://github.com/neuroticsasquat-ch/tvbf/pull/190))
- Fetch episode credits per season and cut over ownership ([NEU-960](https://linear.app/neuroticsasquatch/issue/NEU-960)) ([#191](https://github.com/neuroticsasquat-ch/tvbf/pull/191))
- Season credit backfill pass + admin routes ([NEU-961](https://linear.app/neuroticsasquatch/issue/NEU-961)) ([#194](https://github.com/neuroticsasquat-ch/tvbf/pull/194))
- Prune seasons deleted upstream from the mirror ([NEU-967](https://linear.app/neuroticsasquatch/issue/NEU-967)) ([#197](https://github.com/neuroticsasquat-ch/tvbf/pull/197))

## 0.2.0 — 2026-08-04

### Browse

- Disable browser cache on user-mutable endpoints
- Add show cast and crew routes ([NEU-940](https://linear.app/neuroticsasquatch/issue/NEU-940)) ([#174](https://github.com/neuroticsasquat-ch/tvbf/pull/174))
- Add person detail and credits routes ([NEU-948](https://linear.app/neuroticsasquatch/issue/NEU-948)) ([#175](https://github.com/neuroticsasquat-ch/tvbf/pull/175))
- Add person search and folded person-name index ([NEU-950](https://linear.app/neuroticsasquatch/issue/NEU-950)) ([#176](https://github.com/neuroticsasquat-ch/tvbf/pull/176))
- Add episode guest-cast route ([NEU-949](https://linear.app/neuroticsasquatch/issue/NEU-949)) ([#177](https://github.com/neuroticsasquat-ch/tvbf/pull/177))

### Feedback

- Wire LinearClient settings, lifespan, and dependency
- Add POST /me/feedback route forwarding to Linear
- Send maintainer notification email after Linear submit

### General

- Scope ingest cursor lookup per axis ([NEU-954](https://linear.app/neuroticsasquatch/issue/NEU-954))
- Add credit table definitions and migration ([NEU-936](https://linear.app/neuroticsasquatch/issue/NEU-936)) ([#168](https://github.com/neuroticsasquat-ch/tvbf/pull/168))

### Integrations

- Add Linear GraphQL client for feedback flow
- Use externalId (singular) in customerUpsert

### Observability

- Auto-instrument the API with OpenTelemetry → SigNoz

### Scripts

- Restore all cross-schema FKs on db:refresh ([#180](https://github.com/neuroticsasquat-ch/tvbf/pull/180))
- Add pass A verification script ([NEU-938](https://linear.app/neuroticsasquatch/issue/NEU-938)) ([#181](https://github.com/neuroticsasquat-ch/tvbf/pull/181))
- Retune pass A verification bands to measured totals ([#182](https://github.com/neuroticsasquat-ch/tvbf/pull/182))

### Search

- Fold accents and punctuation in show name search ([NEU-433](https://linear.app/neuroticsasquatch/issue/NEU-433))

### Tvmaze

- Honour show embed and add cast/crew upserts ([NEU-937](https://linear.app/neuroticsasquatch/issue/NEU-937)) ([#169](https://github.com/neuroticsasquat-ch/tvbf/pull/169))
- Alias externals thetvdb so TVDB ids stop parsing as None ([NEU-922](https://linear.app/neuroticsasquatch/issue/NEU-922)) ([#170](https://github.com/neuroticsasquat-ch/tvbf/pull/170))
- Fetch specials on ingest and daily delta ([NEU-933](https://linear.app/neuroticsasquatch/issue/NEU-933)) ([#171](https://github.com/neuroticsasquat-ch/tvbf/pull/171))
- Add pass A show-refresh orchestrator ([NEU-926](https://linear.app/neuroticsasquatch/issue/NEU-926)) ([#172](https://github.com/neuroticsasquat-ch/tvbf/pull/172))
- Add pass C person ingest and guest cast ([NEU-942](https://linear.app/neuroticsasquatch/issue/NEU-942)) ([#178](https://github.com/neuroticsasquat-ch/tvbf/pull/178))
- Add daily person delta ([NEU-943](https://linear.app/neuroticsasquatch/issue/NEU-943)) ([#179](https://github.com/neuroticsasquat-ch/tvbf/pull/179))
- Make the rate limiter process-wide, not per client ([NEU-955](https://linear.app/neuroticsasquatch/issue/NEU-955)) ([#184](https://github.com/neuroticsasquat-ch/tvbf/pull/184))
- Warn when a second rate-limiter budget is created ([NEU-957](https://linear.app/neuroticsasquatch/issue/NEU-957)) ([#185](https://github.com/neuroticsasquat-ch/tvbf/pull/185))

# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-05-16

### Bug Fixes

- Apply email_change enum value on alembic's own connection (#83)

### Features

- Add cookie-auth invite creation with email delivery and admin-scoped invite list (NEU-187) (#98)
- Add is_admin column, require_admin_user dep, and admin user-management routes (NEU-185) (#97)
- Add privacy columns, PATCH toggles, and feed filtering (NEU-180) (#96)
- Add GET /me/feed with cursor pagination and read-time rollup (NEU-178) (#95)
- Emit/cancel activity events from /me mutation services (NEU-174) (#94)
- Add activity_event table and emit/cancel service (NEU-173) (#93)
- Surface my_rating in browse and /me/shows; tighten browse cache (#92)
- Add friend ratings endpoints (#91)
- Add ratings backfill orchestrator and admin endpoints (#90)
- Surface tvmaze rating_average through ingest and browse (#89)
- Add user-rating tables and CRUD endpoints (#88)
- Add GET /me/export streaming JSON endpoint (NEU-158) (#87)
- Add session-revocation endpoints (NEU-155) (#86)
- Add GET /me/sessions + debounce touch (NEU-152) (#85)
- Add PATCH /me for display_name updates (NEU-149) (#84)
- Add forgot-password + reset-password endpoints (NEU-146) (#82)
- Add email-change request + confirm endpoints (NEU-143) (#81)
- Add email-verification endpoints + signup auto-send (NEU-140) (#80)
- Wire Resend + SMTP email provider module (#78)
- Add auth_token table, repo, and service (#77)

### Refactor

- Make clients explicitly inherit from EmailClient protocol (#79)

## [2026-05-10] - 2026-05-10

### Bug Fixes

- Show only the next unaired season per show (#73)
- Set Cache-Control: private on browse routes (NEU-93) (#70)
- Include watched flag on /me list episodes (NEU-100) (#64)
- Accept client-supplied today for watch-next/upcoming bucketing (#48)

### Features

- Add /me/upcoming/{seasons,shows} endpoints (NEU-135) (#72)
- Add first_watched_at to MyShowEntry (NEU-122) (#71)
- Expand Watched sort options to match Active (NEU-114) (#69)
- Add friend engagement endpoints (NEU-111) (#68)
- Add friend library endpoints and connection check (NEU-108) (#67)
- Add /me/watched endpoint (NEU-102) (#66)
- Add block/unblock endpoints + cross-cutting filtering (NEU-78) (#58)
- Add list connections + remove endpoint (NEU-77) (#57)
- Add list/accept/reject connection-request endpoints (NEU-76) (#56)
- Add POST /connection-requests endpoint (NEU-75) (#55)
- Add /users/search endpoint with block filtering (NEU-74) (#54)
- Add connection repo, service, and schemas (NEU-73) (#53)
- Add app.connection model and migration (NEU-72) (#52)
- Redefine airdate_desc as last-aired, add unwatched_airdate_desc (#44)

### Refactor

- Rename dto modules to schemas (FastAPI convention) (#49)

## [2026-05-06] - 2026-05-06

### Bug Fixes

- Accept client-supplied today for watch-next/upcoming bucketing (#48)

### Refactor

- Rename dto modules to schemas (FastAPI convention) (#49)

## [2026-05-05] - 2026-05-05

### Features

- Redefine airdate_desc as last-aired, add unwatched_airdate_desc (#44)

## [2026-05-04] - 2026-05-05

### Features

- Include matched_aka in search responses (#41)

## [2026-05-03] - 2026-05-03

### Features

- Match shows by TVMaze AKA titles (#38)
- Add show-level bulk watch and per-season progress endpoints (#37)
- Add last_aired sort key to /shows (#36)
- Expose aired counts, last-watched, and added_at on list entries (#35)
- Add aired and upcoming episode counts per entry (#34)
- Expose last_watched_at and last_aired per entry (#28)

## Frontend release history

Until 0.4.0 the frontend was its own repo, `tvbf-frontend`, released in lockstep with the backend
under the same version tags. Its notes are kept below as they were written, with their PR links
pointed at that repo. From the monorepo merge on, each release has one set of notes, above
(NEU-2235).

### 0.4.0 — 2026-09-27

#### Episode

- Place guest cast and crew into tabs ([NEU-1209](https://linear.app/neuroticsasquatch/issue/NEU-1209))

#### General

- Web manifest, icons and apple-touch-icon for installability ([NEU-1482](https://linear.app/neuroticsasquatch/issue/NEU-1482)) ([#251](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/251))

#### Person

- Place cast, guest, crew, and episode crew into tabs ([NEU-1210](https://linear.app/neuroticsasquatch/issue/NEU-1210))
- Move count to tab and hide empty tabs ([NEU-1211](https://linear.app/neuroticsasquatch/issue/NEU-1211))

#### Push

- Subscription lifecycle and Settings Notifications state line ([NEU-1487](https://linear.app/neuroticsasquatch/issue/NEU-1487)) ([#253](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/253))
- Notification toggles and device list in Settings ([NEU-1491](https://linear.app/neuroticsasquatch/issue/NEU-1491))
- Per-show mute control on My Shows rows and cards ([NEU-1495](https://linear.app/neuroticsasquatch/issue/NEU-1495)) ([#255](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/255))
- One-time post-add nudge card and Install app button ([NEU-1492](https://linear.app/neuroticsasquatch/issue/NEU-1492)) ([#256](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/256))

#### Pwa

- Hand-written service worker for Web Push ([NEU-1483](https://linear.app/neuroticsasquatch/issue/NEU-1483)) ([#252](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/252))

### 0.3.4 — 2026-08-23

#### General

- Disambiguate friend-mode filter labels with Their/My split and group dividers
- Normalize Their/My filter labels and correct disabled filter on friend Active tab
- Add disabledReason to TheirShowsFilterPicker
- Add Activity tab to friend profile and remove Activity from Friends page
- Use direct import instead of import() type in FriendActivityFeed

### 0.3.3 — 2026-08-23

#### Discover

- Make My Recommendations a tab, first and default
- Stop rendering the recommendation reason
- Refresh the recommendations grid after an add ([NEU-1176](https://linear.app/neuroticsasquatch/issue/NEU-1176))
- Hold the recommendations latch above the tab pane ([NEU-1176](https://linear.app/neuroticsasquatch/issue/NEU-1176))
- A dismiss control on a recommendation card ([NEU-1179](https://linear.app/neuroticsasquatch/issue/NEU-1179))

#### General

- Mark tracked shows on search results and the Similar tab ([NEU-1186](https://linear.app/neuroticsasquatch/issue/NEU-1186))
- One add/remove control, suppressed where it cannot act ([NEU-1187](https://linear.app/neuroticsasquatch/issue/NEU-1187))
- Carry the same facts and controls in grid and list views ([NEU-1188](https://linear.app/neuroticsasquatch/issue/NEU-1188))
- Extract the post-removal focus move and apply it to watch history ([NEU-1193](https://linear.app/neuroticsasquatch/issue/NEU-1193))
- Collapse duplicate row links, split empty states, name languages ([NEU-1190](https://linear.app/neuroticsasquatch/issue/NEU-1190))
- Render field validation errors from 422 responses ([NEU-1196](https://linear.app/neuroticsasquatch/issue/NEU-1196))
- Match field errors on shape, clear them on edit ([NEU-1196](https://linear.app/neuroticsasquatch/issue/NEU-1196))
- Render field errors on password reset, share the form half ([NEU-1196](https://linear.app/neuroticsasquatch/issue/NEU-1196))
- Answer a token complaint with the bad-link copy ([NEU-1196](https://linear.app/neuroticsasquatch/issue/NEU-1196))
- Add the Turnstile widget to the signup form ([NEU-1166](https://linear.app/neuroticsasquatch/issue/NEU-1166))
- Explain the verification gate before the click ([NEU-1167](https://linear.app/neuroticsasquatch/issue/NEU-1167))
- Admin disable toggle and report-user action ([NEU-1168](https://linear.app/neuroticsasquatch/issue/NEU-1168))
- Collect a handle at signup ([NEU-1198](https://linear.app/neuroticsasquatch/issue/NEU-1198))
- Surface handles in signup, settings, search and profiles ([NEU-1169](https://linear.app/neuroticsasquatch/issue/NEU-1169))
- Split the report dialog's naming and close the empty-handle hole ([NEU-1169](https://linear.app/neuroticsasquatch/issue/NEU-1169))
- Add terms, privacy, about, and contact pages ([NEU-1170](https://linear.app/neuroticsasquatch/issue/NEU-1170))
- Make invite code optional on signup ([NEU-1171](https://linear.app/neuroticsasquatch/issue/NEU-1171))
- Add hero page

#### Library

- Attribute every rating and library mark to its owner ([NEU-1181](https://linear.app/neuroticsasquatch/issue/NEU-1181))

#### Ratings

- Give each rating kind its own treatment ([NEU-1182](https://linear.app/neuroticsasquatch/issue/NEU-1182))
- Keep the aggregate's fill at five-star density ([NEU-1182](https://linear.app/neuroticsasquatch/issue/NEU-1182))

#### Search

- Add a My Shows control to results in both views ([NEU-1192](https://linear.app/neuroticsasquatch/issue/NEU-1192))

#### Shows

- Move More Like This into a Similar tab

### 0.3.2 — 2026-08-16

#### Discover

- Add the Trending tab to the Discover page ([NEU-1057](https://linear.app/neuroticsasquatch/issue/NEU-1057)) ([#190](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/190))
- Add the Most Anticipated tab ([NEU-1060](https://linear.app/neuroticsasquatch/issue/NEU-1060)) ([#191](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/191))

#### General

- Render the "More like this" section on show pages ([NEU-1054](https://linear.app/neuroticsasquatch/issue/NEU-1054)) ([#189](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/189))

### 0.3.1 — 2026-08-16

#### Discover

- Add the /discover route, nav item, and page shell ([NEU-1113](https://linear.app/neuroticsasquatch/issue/NEU-1113)) ([#185](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/185))
- Render the "Recommended for you" section ([NEU-1114](https://linear.app/neuroticsasquatch/issue/NEU-1114)) ([#186](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/186))

### 0.3.0 — 2026-08-14

#### Footer

- Swap attribution from TV Maze to TMDB ([NEU-1049](https://linear.app/neuroticsasquatch/issue/NEU-1049)) ([#176](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/176))
- Remove the TVmaze CC BY-SA credit ([NEU-1147](https://linear.app/neuroticsasquatch/issue/NEU-1147))
- Restore the TVmaze CC BY-SA credit on its own line
- Pair the attribution and publisher blocks on wide viewports

#### Friends

- Label a specials-season roll-up by name ([NEU-1133](https://linear.app/neuroticsasquatch/issue/NEU-1133))
- Name a special beside its bare "S1" in the feed ([NEU-1134](https://linear.app/neuroticsasquatch/issue/NEU-1134))

#### Friends-feed

- Render a special's null episode number without "Enull" ([NEU-1131](https://linear.app/neuroticsasquatch/issue/NEU-1131))

#### General

- Adopt TMDB's status vocabulary in the show filter ([NEU-1037](https://linear.app/neuroticsasquatch/issue/NEU-1037))
- Surface episode counts on cast credits ([NEU-1041](https://linear.app/neuroticsasquatch/issue/NEU-1041))
- Label the specials season by name rather than "Season 0" ([NEU-1129](https://linear.app/neuroticsasquatch/issue/NEU-1129))

#### Person

- Unify the episode row separator with the friends feed

### 0.2.2 — 2026-08-07

#### Person

- Group filmography credits by show ([NEU-1007](https://linear.app/neuroticsasquatch/issue/NEU-1007)) ([#162](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/162))
- Make the whole episode row clickable and space the targets ([#163](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/163))
- Cap the episodes listed in an expanded credit group ([#164](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/164))

### 0.2.1 — 2026-08-06

#### Episode

- Add an episode crew section to the episode page ([NEU-964](https://linear.app/neuroticsasquatch/issue/NEU-964)) ([#158](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/158))

#### Person

- Add episode crew credits to the person page ([NEU-965](https://linear.app/neuroticsasquatch/issue/NEU-965)) ([#159](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/159))

### 0.2.0 — 2026-08-04

#### Ci

- Merge main into dependency branch via PR instead of force-push

#### Episodes

- Add guest cast section to the episode page ([NEU-952](https://linear.app/neuroticsasquatch/issue/NEU-952)) ([#154](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/154))

#### Feedback

- Add useSubmitFeedback mutation hook + MSW handler
- Add FeedbackDialog component
- Expose FeedbackDialog from the account menu

#### General

- Mask Sentry replays and upload source maps on prod build ([NEU-424](https://linear.app/neuroticsasquatch/issue/NEU-424))
- Add cast and crew sections to the show detail page ([NEU-941](https://linear.app/neuroticsasquatch/issue/NEU-941)) ([#150](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/150))
- Add person page and /people/:id route ([NEU-951](https://linear.app/neuroticsasquatch/issue/NEU-951)) ([#152](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/152))
- Add a People section to search results ([NEU-953](https://linear.app/neuroticsasquatch/issue/NEU-953)) ([#153](https://github.com/neuroticsasquat-ch/tvbf-frontend/pull/153))

#### Shows

- Combine seasons, cast and crew into one tabbed section ([NEU-956](https://linear.app/neuroticsasquatch/issue/NEU-956))

#### Types

- Extract typed AuthedUser local for setQueryData updater

# Changelog

All notable changes to this project will be documented in this file.

### [0.1.0] - 2026-05-16

#### Features

- Add Invites tab to AdminPage and prefill signup form from URL params (NEU-188) (#99)
- Add /admin route with Users tab and conditional UserMenu link (NEU-186) (#98)
- Polish Friends tab with nav link, icons, infinite scroll, empty + loading states (NEU-182) (#97)
- Add activity privacy toggles to Settings and ShowDetailPage (NEU-181) (#96)
- Add useFeed hook and minimal /friends page (NEU-179) (#95)
- Surface my-rating across cards and library sort/filter (NEU-172) (#94)
- Show friend ratings on show + episode pages (#93)
- Add half-star rating input on show + episode pages (#92)
- Add 'Download my data' button (NEU-159) (#91)
- Add session revoke + log-out-everywhere controls (NEU-156) (#90)
- Add active-sessions list (NEU-153) (#89)
- Add /forgot-password + /reset-password pages (NEU-147) (#88)
- Add change-email UI + confirm page (NEU-144) (#87)
- Add unverified-email banner + /verify-email landing page (NEU-141) (#86)
- Add /settings page with display-name edit (NEU-150) (#85)

### [2026-05-10] - 2026-05-10

#### Bug Fixes

- Disable spellcheck on search inputs (NEU-133) (#80)
- Remove redundant "n/a" tag on disabled options (NEU-132) (#78)
- Disable In My Shows picker on Active tabs (NEU-131) (#77)
- Drop per-show watched fetch in list rows (NEU-100) (#56)
- Hide mobile bottom nav while a text input is focused (#50)
- Send local today on watch-next/upcoming/my-shows requests (#49)

#### Features

- Add Seasons and Shows tabs to Upcoming page (NEU-136) (#81)
- Collapse long show/episode/season summaries with toggle (NEU-125) (#79)
- Add caller watch-state filter on friend tabs (NEU-130) (#76)
- Add caller-relative My Library filter on friend tabs (NEU-129) (#75)
- Add caller-relative row indicators on friend lists (NEU-128) (#74)
- Wire FriendProfilePage tabs to shared library views (NEU-127) (#73)
- Align Active and All Watched toolbars (NEU-123) (#71)
- Add To Be Determined filter; rename Upcoming to In Development (NEU-119) (#69)
- Add Upcoming status filter (NEU-118) (#68)
- Align Watched sort picker with Active (NEU-115) (#67)
- Surface friend engagement on show + episode pages (NEU-112) (#66)
- Add Remove from history action on Watched rows (NEU-105) (#65)
- Add Watched row UI with In My Shows quick-toggle (NEU-104) (#64)
- Add Watched sub-tab on MyShowsPage (NEU-103) (#63)
- Add friend profile page (NEU-109) (#62)
- Add blocked list and block actions (NEU-83) (#61)
- Add connections list and remove flow (NEU-82) (#60)
- Add requests inbox with optimistic actions (NEU-81) (#59)
- Add user search + connect flow (NEU-80) (#58)
- Add connections route shell and API client (NEU-79) (#57)
- Fix Last Aired sort and add Newest Unwatched option (#45)

#### Refactor

- Extract Library{Active,Watched}List shared components (NEU-126) (#72)
- Polish My Shows + All Watched list rows (#70)

### [2026-05-06] - 2026-05-06

#### Bug Fixes

- Hide mobile bottom nav while a text input is focused (#50)
- Send local today on watch-next/upcoming/my-shows requests (#49)

### [2026-05-05] - 2026-05-05

#### Features

- Fix Last Aired sort and add Newest Unwatched option (#45)

### [2026-05-04] - 2026-05-05

#### Bug Fixes

- Keep overlay open when interacting with filter sheet (#42)
- Keep footer visible above mobile nav and search overlay (#41)
- Stop iOS Safari auto-zoom on search input focus (#39)

#### Features

- Link site title back to home (#40)
- Show matched AKA on foreign-titled results (#38)

### [2026-05-03] - 2026-05-03

#### Features

- Overhaul show/season/episode pages and add header search (#35)
- Show episode thumbnail with title above row (#34)
- Restructure Watch Next/Upcoming/My Shows with filters and sort (#33)
- Align Upcoming with Watch Next layout and add watch progress bar
- Make Watch Next the home page and overhaul its UI (#25)
