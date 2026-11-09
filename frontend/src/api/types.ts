/**
 * The API's DTOs, named for the app, plus the FE-internal types that sit beside them.
 *
 * Every wire shape here is an alias onto `schema.d.ts`, which `task fe:generate` writes from the
 * committed `openapi.json` and CI's `api-types` job keeps in step with the backend (NEU-2261). Do
 * not hand-write a response type: one that disagrees with the server is the drift the generated
 * file exists to make impossible. A changed response model shows up here as a type error at the
 * call site that relied on the old shape, before merge.
 *
 * Field-level documentation lives on the backend's Pydantic models; what stays here is what is
 * specific to how the SPA uses a shape.
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

// --- FE-internal: query parameters and the client-side sorts ---------------------------------

/** The `sort` keys `GET /shows` accepts. The route types `sort` as a bare string (the whitelist is
 * `ALLOWED_SORT_KEYS`, enforced as a 422), so the keys are listed here rather than generated. */
export type SortKey =
  | "name"
  | "-name"
  | "premiered"
  | "-premiered"
  | "tvmaze_updated"
  | "-tvmaze_updated"
  | "last_aired"
  | "-last_aired"
  | "popularity"
  | "-popularity";

export const ALL_SORT_KEYS: readonly SortKey[] = [
  "name",
  "-name",
  "premiered",
  "-premiered",
  "tvmaze_updated",
  "-tvmaze_updated",
  "last_aired",
  "-last_aired",
  "popularity",
  "-popularity",
] as const;

export interface ShowFilters {
  search?: string;
  status?: string;
  genre?: string[];
  network?: number[];
  language?: string;
  type?: string;
  sort?: SortKey;
  page?: number;
  per_page?: number;
}

export type MyShowsSort = "recent_activity" | "name_asc" | "name_desc" | "added";
export type WatchNextSort =
  | "last_aired_desc"
  | "last_watched_desc"
  | "oldest_unwatched_asc"
  | "newest_unwatched_desc"
  | "added_desc"
  | "name_asc";
export type UpcomingSort = "airdate_asc" | "airdate_desc" | "added_desc" | "name_asc" | "name_desc";
export type WatchedSort =
  | "name_asc"
  | "last_watched_desc"
  | "last_aired_desc"
  | "premiered_asc"
  | "premiered_desc"
  | "first_watched_desc";
export type WatchedStatusFilter = "all" | WatchedStatus;

// --- Catalog ---------------------------------------------------------------------------------

export type NetworkRef = Schemas["NetworkRef"];
export type NetworkOut = Schemas["NetworkOut"];
export type GenreOut = Schemas["GenreOut"];
export type ExternalsOut = Schemas["ExternalsOut"];
export type SeasonOut = Schemas["SeasonOut"];

/** `watched` is filled by the `/me/*` list endpoints and null on catalog-browse endpoints, which
 * have no user context. */
export type EpisodeOut = Schemas["EpisodeOut"];

/** Nested inside six `/me` payloads (`MyShowEntry.show`, watch-next, upcoming, …) and the base of
 * `ShowDetail`, none of which the server computes a library mark for — which is why the mark is
 * on the surface types below and not here. */
export type ShowSummary = Schemas["ShowSummary"];
export type ShowDetail = Schemas["ShowDetail"];

/** A `ShowSummary` carrying the viewer's library mark: the shape every grid surface serves
 * (NEU-1184 §2.1, §5.1). Each surface keeps its own generated type and its own rules for
 * `my_rating`; this is the part they share, which is what `ShowGrid` / `ShowCard` accept.
 *
 * `in_my_shows` is a **mark, never a filter**: a tracked show still appears in every list it
 * would otherwise appear in. */
export type MarkedShow = ShowSummary & { in_my_shows: boolean };

/** One entry of `GET /trending`, flattened rather than nested under a `show` key so `ShowGrid` /
 * `ShowCard` take it as is (NEU-1056 §2). */
export type TrendingShow = Schemas["TrendingShowOut"];

/** The `GET /trending` body. `captured_at` is null exactly when `shows` is empty, and a stale
 * snapshot is served as the same empty body an empty table gives (contract §3), so this client
 * can neither re-derive the seven-day cutoff nor tell the two apart — the cutoff is the server's
 * rule, enforced in one place. */
export type TrendingSnapshot = Schemas["TrendingOut"];

/** One entry of `GET /anticipated`. The body is a bare array: nothing is stored, so there is no
 * `captured_at` and no staleness rule (NEU-1059 §3). `premiered` stays nullable though the server
 * never sends an undated show (§5) — the card renders "TBA" rather than trusting that. `my_rating`
 * is always null here: every entry premieres in the future. */
export type AnticipatedShow = Schemas["AnticipatedShowOut"];

/** One item of `GET /shows` — browse and search results (NEU-1186). The route answers
 * `private, no-store`, so `useShows` keeps its five-minute `staleTime`: invalidation, not
 * `staleTime`, keeps the mark fresh (spec §5.2). */
export type BrowseShow = Schemas["BrowseShowOut"];

/** One row of `GET /shows/{id}/similar` — TMDB's "More like this" (NEU-1186). Both `in_my_shows`
 * and `my_rating` are filled. `genres` is always `[]` and `network` always null: `ShowCard`
 * renders neither. */
export type SimilarShow = Schemas["SimilarShowOut"];

export type ShowListPage = Schemas["ShowListPage"];

// --- Credits and people ----------------------------------------------------------------------

export type PersonRef = Schemas["PersonRef"];
export type CharacterRef = Schemas["CharacterRef"];

/** What `episode_count` means depends on the route (NEU-1512 §4.1): the show's aggregate on
 * `/shows/{id}/cast` and `/guest-cast`, appearances in the season for a season's guests, and null
 * for a season's regulars and on an episode's guest cast. */
export type CastMember = Schemas["CastMemberOut"];
export type CrewMember = Schemas["CrewMemberOut"];

/** `GET /shows/{id}/seasons/{number}/cast`: a season's regulars in billing order, then its guests
 * by appearances. */
export type SeasonCast = Schemas["SeasonCastOut"];

export type PersonOut = Schemas["PersonOut"];
export type ShowRef = Schemas["ShowRef"];
export type EpisodeRef = Schemas["EpisodeRef"];

/** The glossary keeps *series crew credit* (`PersonCrewCredit`) and *episode crew credit*
 * (`PersonEpisodeCrewCredit`) apart: a job held across the series, or one held episode by
 * episode. */
export type PersonCastCredit = Schemas["PersonCastCreditOut"];
export type PersonCrewCredit = Schemas["PersonCrewCreditOut"];
export type PersonGuestCredit = Schemas["PersonGuestCreditOut"];
export type PersonEpisodeCrewCredit = Schemas["PersonEpisodeCrewCreditOut"];

/** All four keys are always present — an absent category is an empty array, never a missing
 * key. */
export type PersonCredits = Schemas["PersonCreditsOut"];
export type PersonListPage = Schemas["PersonListPage"];

// --- Ratings and recommendations -------------------------------------------------------------

export type ShowRating = Schemas["ShowRatingOut"];
export type EpisodeRating = Schemas["EpisodeRatingOut"];

/** One row of `GET /me/recommendations`, flattened with the model's `rank` (NEU-1112 §2). `rank`
 * is the stored rank, so it is not guaranteed contiguous or to start at 1.
 *
 * **There is no `reason`.** The server stopped serving it on 2026-08-17; it is still stored as a
 * diagnostic, so do not add it back on the strength of finding it in the database. */
export type Recommendation = Schemas["RecommendationOut"];
export type RecommendationsResponse = Schemas["RecommendationsOut"];

// --- The viewer's library --------------------------------------------------------------------

/** `muted` and `hide_from_activity` are optional here though `GET /me/shows` always sends them:
 * the Watched grid adapts a `WatchedEntry` into this shape, and that payload carries neither.
 *
 * `my_rating` is the caller's own rating, hydrated beside `show` (whose own `my_rating` stays
 * null). */
export type MyShowEntry = Omit<Schemas["MyShowEntry"], "muted" | "hide_from_activity"> &
  Partial<Pick<Schemas["MyShowEntry"], "muted" | "hide_from_activity">>;

/** `my_rating` is **the row owner's rating, not the requester's** (NEU-1191): the same user on
 * `GET /me/watched`, the *friend* on `GET /users/{id}/watched`. It is attributed through
 * `ratingOwnerFor` (NEU-1181) rather than assumed to be the viewer's. */
export type WatchedEntry = Schemas["WatchedEntry"];
export type WatchedStatus = WatchedEntry["status"];

export type WatchNextEntry = Schemas["WatchNextEntry"];
export type UpcomingEntry = Schemas["UpcomingEntry"];
export type UpcomingSeasonEntry = Schemas["UpcomingSeasonEntry"];
export type UpcomingShowEntry = Schemas["UpcomingShowEntry"];
export type EpisodeWatchOut = Schemas["EpisodeWatchOut"];
/** A season or whole-show mark: how many episodes it marked. */
export type BulkSeasonResult = Schemas["BulkSeasonResult"];
export type SeasonProgress = Schemas["SeasonProgress"];

// --- Accounts and admin ----------------------------------------------------------------------

/** `handle` is lowercase, unique and `^[a-z][a-z0-9_]{2,29}$`; the server normalises case and a
 * leading `@` rather than refusing them, so what is stored is not always what was typed
 * (NEU-1163). */
export type AuthedUser = Schemas["AuthedUserOut"];

/** What the SPA sends `PATCH /me/preferences`: any subset of the viewer's switches. Narrower
 * than the route's `MePreferencesUpdate`, which also takes `null` for "leave it": the SPA never
 * sends one, and merges the patch straight into the cached `AuthedUser`. */
export type PreferencesPatch = Partial<
  Pick<
    AuthedUser,
    | "activity_feed_enabled"
    | "notify_airs_today"
    | "notify_premiere_set"
    | "notify_premiere_moved"
    | "notify_ended"
    | "notify_revived"
  >
>;

/** `disabled_at` is on the admin list alone. `AuthedUserOut` deliberately does not carry it: a
 * disabled user reaches no other surface, and a field saying so would be the machine-readable
 * confirmation the backend refuses to hand an abuser (NEU-1162 §2.2). */
export type AdminUserRow = Schemas["AdminUserOut"];

/** One UTC day of `GET /admin/push/stats` (NEU-1493). `retired` is a subset of `failed`. */
export type AdminPushStatsDay = Schemas["PushStatsDay"];
/** Live totals plus exactly 30 UTC days, oldest first, zero-filled (project spec §5.4). */
export type AdminPushStats = Schemas["PushStatsOut"];
export type InviteRow = Schemas["InviteOut"];

/** One row of `GET /me/sessions`. */
export type SessionSummary = Schemas["SessionSummary"];

// --- Push ------------------------------------------------------------------------------------

export type VapidPublicKey = Schemas["VapidPublicKeyOut"];
export type PushSubscriptionSummary = Schemas["PushSubscriptionOut"];
export type PushSubscriptionCreated = Schemas["PushSubscriptionCreated"];

/** `POST /me/push/test`'s 202 body: the outcome, not a bare accepted (§5.4). */
export type PushTestResult = Schemas["PushTestOut"];

// --- Connections and the feed ----------------------------------------------------------------

/** Every payload that names a user carries `handle` beside `display_name` (NEU-1163 §7), drawn
 * through `UserIdentity`, which owns the `@` sigil. */
export type UserBrief = Schemas["UserBrief"];
export type UserSearchResult = Schemas["UserSearchResult"];

export type ConnectionRequestOut = Schemas["ConnectionRequestOut"];
export type ConnectionState = ConnectionRequestOut["state"];
export type ConnectionRequestList = Schemas["ConnectionRequestList"];
export type ConnectionOut = Schemas["ConnectionOut"];
export type BlockedUserOut = Schemas["BlockedUserOut"];

export type ShowFriendActivity = Schemas["ShowFriendActivity"];
export type FriendRating = Schemas["FriendRatingItem"];
export type FriendRatingsResponse = Schemas["FriendRatingsResponse"];

/** One entry of `GET /me/friends/popular`. `friend_count` counts distinct accepted connections
 * with visible activity in the window, so it is ≥ 1; the viewer sees a count, never a name, on
 * this surface (popular-with-friends project spec §7). */
export type PopularShow = Schemas["PopularShowOut"];

/** `shows` is in the server's rank order and never re-sorted here. `connection_count` is what
 * tells the two empty cases apart — nobody to hear from, or nobody saying anything (§5.2);
 * `window_days` is informational and never computed with (§7). */
export type PopularWithFriends = Schemas["PopularWithFriendsOut"];

export type FeedItem = Schemas["FeedItem"];
export type FeedKind = FeedItem["kind"];
export type FeedShowMini = Schemas["ShowMini"];

/** `number` is null for a copied TV Maze special (NEU-1062); `FeedItemRow` drops the `E` segment
 * and puts `name` in its place (NEU-1134). */
export type FeedEpisodeMini = Schemas["EpisodeMini"];
export type FeedPage = Schemas["FeedPage"];
