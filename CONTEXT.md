# Animee

Streaming product (intended domain: animee.uz) for anime, drama, film, and serial. Catalog, playback, lists, Profile, Settings, Watch Party, and the dashboard live in this one context.

## Language

**Animee**:
The product name. The public site is intended to be animee.uz.
_Avoid_: AniStream, AniSayt (old UI and repo names, not the product)

**Guest**:
A person watching without an account. May play episodes. May not keep lists, join a Watch Party, comment, or persist progress.
_Avoid_: anonymous user, visitor

**User**:
A registered person. May keep lists, join a Watch Party, comment, and persist progress. Signs in with Google, Telegram, or email.
_Avoid_: member, account, customer, viewer (when you mean the registered person)

**Admin**:
A User who may manage the catalog, Masters, other Users, Moderators, Notices, Watch Parties, and the dashboard (`/dashboard/`).
_Avoid_: staff, superuser (Django's word)

**Genre**:
A named category of Anime.
_Avoid_: Ganre (legacy typo)

**Anime**:
A catalog title. It has a Kind. Seasonal titles show Seasons in the UI; non-seasonal titles hide Season in the UI but still have one internal Season.
_Avoid_: show, series (when you mean the catalog title)

**Kind**:
Whether an Anime is anime, drama, film, or serial. The Uzbek UI says Kino for film and Serial for serial. Each Kind has its own dashboard list and create form.
_Avoid_: type, category (when you mean this), movie as the domain term

**Lists**:
A User's watching, completed, planned, dropped, and favorite titles. The User opens and edits them on `/lists/`. Distinct from Profile.
_Avoid_: profile as the lists page, watchlist (when you mean this page)

**Settings**:
A User's private account edits: username, bio, photo, playback, Notice delivery, and Telegram link.
_Avoid_: preferences as the page name

**Notice**:
A User-facing message stored in their inbox — a new Season, Episode, or site news. The User opens the inbox to read it. Telegram is an extra delivery channel when the User has a Telegram link and allows Notices.
_Avoid_: notification as the entity, push, alert (when you mean this)

**Telegram link**:
Connecting an existing User to a Telegram account so Notices can be delivered. Distinct from signing in with Telegram.
_Avoid_: Telegram login (when you mean this connect step)

**Season**:
A numbered batch of Episodes on an Anime of Kind anime, drama, or serial. Film hides Season in the UI but still has one internal Season. The dashboard creates a Season on its own page after the Anime exists.
_Avoid_: part (when you mean Season)

**Episode**:
One watchable installment of a Season. A Film has a single Episode; extra languages are Masters on that Episode, not more Episodes.
_Avoid_: qism, seriya as domain terms (those are UI translations)

**Sequel**:
The next Film a User may open after finishing this Film. Each Film is its own Anime, created separately and linked. Not used for seasonal Kind.
_Avoid_: next episode, next season (when you mean the next Film)

**Master**:
The language-specific video file for an Episode (for example UZ dub or RU dub). An Admin or Moderator ingests it by uploading a video file or by sending an internet video URL; the system downloads the file and derives HLS. They never paste an HLS URL. Telegram ingest remains a later path.
_Avoid_: Video as the uploaded object (legacy model name), source file, HLS URL as the ingest input

**Rendition**:
A quality level (360p–1080p) derived from a Master. The player may switch Rendition while playback continues.
_Avoid_: quality file (as if the Admin uploaded it), variant as the upload

**Subtitle**:
Optional timed text for an Episode in UZ or RU. Chosen in the player; not burned into the Master.
_Avoid_: caption (Telegram's word), hardsub

**Review**:
A User's written comment and rating on an Anime.
_Avoid_: Comment (when you mean the Episode thread), feedback

**Comment**:
A User's written message on an Episode. A Comment may reply to another Comment. Guests may read; only a User may write or like.
_Avoid_: Review (that's the Anime rating), chat (that's Watch Party), izoh as the domain term (that is the Uzbek UI label)

**Like**:
A User's approval of an Episode or a Comment. One per User per target.
_Avoid_: reaction, upvote (when you mean this)

**Moderator**:
A User who may manage the catalog and Masters from `/dashboard/` (Anime, Kino, Drama, Serial). May not manage other Users, Notices, Watch Parties, or the Player poster.
_Avoid_: admin (when you mean this role)

**List**:
A User's status on an Anime: watching, favorite, completed, dropped, or plan to watch. One row per User per Anime, not a table per status.
_Avoid_: playlist, watchlist (when you mean this status), separate tables per status

**Player poster**:
The site's branded image shown on the player over every Episode until playback starts. One current image; Admin replaces it from the dashboard.
_Avoid_: watermark, thumbnail (that's the Episode still), cover (when you mean the Anime poster), splash

**Progress**:
A User's saved position in an Episode. Guests have none.
_Avoid_: bookmark, history (when you mean the seconds offset)

**Ingest session**:
An Admin-started queue in the admin panel that binds the next Telegram files to a Season and a dub language, asking for each Episode in order.
_Avoid_: upload job (when you mean this queue), bot chat as the source of truth

**Streak**:
A User's consecutive watch days. Watching an Episode for at least 30 seconds on a calendar day adds 1 and lights the flame. If they have not watched yet today, only they see the grey flame with a warning. Other people see the count, not that they missed today. Missing a day resets the current count; the longest run is kept. Shown on Profile next to the display name.
_Avoid_: Olovcha, Ugolek, XP, ADMIN as this chip, streak freeze

**Search**:
The site-wide overlay. All looks through catalog titles of every Kind and never returns Users. Users is a separate scope. History is the last queries and opened hits, kept on the device.
_Avoid_: mixing Users into All, Neon/Sakura mood chips as search hints

**Profile report**:
A User's complaint about another Profile: a target (photo, banner, nick, or bio) and a required reason (insult/trolling, racism, hate, threat, harassment, porn, spam, scam, impersonation, or other). The owner of a Profile does not see this; they see edit. Guests must sign in. False reports can warn, then mute reporting. Admin reviews reports from `/dashboard/`.
_Avoid_: ticket, flag as the entity name

**Ban**:
An Admin lock on a User account. The User can still sign in, then sees the ban page: reason, optional unban request, and logout. Some Bans refuse the request. Staff cannot be banned.
_Avoid_: is_active as this lock, kick, timeout (when you mean Ban)

**Restriction**:
An Admin lock on a User's ability to change or remove username, photo, banner, or bio, or to write Comments. Distinct from Ban.
_Avoid_: mute (that's report mute), Ban (that's the account lock)

**Profile**:
A User's public page: banner with avatar and display name on it, username, Streak, status line, bio, up to ten latest watching posters, up to five favorite slots, and a facts sheet (joined date, last login, role, comments, episodes with Progress). The owner may edit the look from that page and may hide watching posters from others. Full Lists live on `/lists/`, not here.
_Avoid_: account page (when you mean Settings), wall, lists page

**Profile banner**:
A User-chosen wide image on their Profile. Distinct from the Player poster.
_Avoid_: cover (when you mean this), Player poster, splash

**Watch Party**:
A live shared viewing of one Episode. Users join by invite link (Guests cannot). The link first opens an invite gate; the host may require camera or mic permission before Join. A Guest may see the gate, then must become a User (and return to the room). Playback is synchronized, the room has chat, and members may turn on camera/mic faces. The host picks the Anime (any Kind) and starting Episode when creating the room. An Admin may skip the room to the next Episode from `/dashboard/`. An open Watch Party closes itself if the Episode is not being watched for four hours. The Uzbek UI label is Birgalikda. The entity is WatchParty.
_Avoid_: room as the product name, Birgalikda as the domain term (that is the Uzbek UI label)
