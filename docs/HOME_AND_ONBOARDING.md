# Home and onboarding (UI-1)

The product opens as a chat-style interface: a welcoming screen first, no login wall. Signing in or
registering happens inside the conversation when the visitor chooses. Once the app knows who they are it
loads their details and shows workflow cards for their role. A workflow opens in a workspace panel
(beside the chat on 1280 px and wider, a full-screen sheet below that). The chat stays as home and history.

## Layout

* Collapsible left sidebar, a centred greeting (time of day plus nickname; a generic friendly greeting
  for guests) in a self-hosted OFL serif display font, one large rounded composer that grows to five
  lines with mode chips beneath it, and a row of three suggestion cards. A dismissible tip banner is allowed.
* Own identity: a `Brand` component (wordmark and colours in one tokens file). No other product's name,
  logo, illustrations or exact palette.
* The composer is a deterministic topic or student finder. It generates no answers; Ask stays off.
  Nothing typed is stored or logged (not in the browser history store, not at the API, not in the
  database); PII (emails, phone numbers, name-like patterns) is stripped before matching; moderation runs
  on input; matches appear as "Did you mean" chips; text outside the syllabus gets "not in your syllabus yet".

## Roles (one account, one role; the home follows the role)

| Role | Cards | Sidebar | Composer modes |
| --- | --- | --- | --- |
| Guest | pick my class, try a lesson, practise a few | New chat, Create account | Learn, Practise |
| Student | Continue (current skill and progress), Review due (count), Today's plan (minutes left) | New chat, Today, Chapters, Revision, My notes (disabled). Pinned: current chapter. Recent: structured session summaries only | Learn, Practise, Revise, Notes (disabled, "coming soon") |
| Teacher | Class heatmap, Stuck now, Review queue | Classes, Heatmap, Stuck now, Review queue, Reports | Class, Alerts, Content |
| Parent | This week, Consent, Add a child | Children, Weekly report, Consent, My data | Progress, Privacy |

Teacher and parent homes are thin shells that open the existing views in the panel with no behaviour change.
Teacher views stay filtered to students whose guardians granted `teacher_share`.

## Setup conversation (tappable chips)

Class, state, board, medium, subject, in that order. Options come from the registry and config
(`GET /guest/context`), never from code literals. A step whose registry data is missing is skipped (the
registry has no states or media today). An option without live content shows "coming soon" and cannot
start. Guest choices are saved on the device only (`localStorage`); nothing about a guest is stored on a
server until a guardian creates the account.

## Create account

Offered in the sidebar footer and as an in-chat card. Three paths, all through the existing auth, with
consent scopes validated on the server:

* **Student:** family code and PIN, or "ask a grown-up", which starts the existing guardian flow
  (guest upgrade). **Students under 18 never create accounts alone.**
* **Teacher:** email code plus the staff-assigned school code.
* **Parent:** email code.

## Conversation state machine

A pure module with four phases: `welcome` (greeting, role unknown), `context` (setup chips),
`identity` (sign in, just try it, save my progress, parent, teacher, create account), `home` (role cards).
Transitions are driven by user choices only; the module has unit tests and no side effects.

## Panel and history

Workflows (chapter map, skill path, lesson, practice, done, teacher and parent views) render the existing
screens inside the panel. Deep links, browser back and refresh work, and the old routes (`/today`,
`/chapters`, ...) keep working. When a workflow ends the chat gets a short structured summary message
(skill, result, next step); free-text transcripts are never kept.
