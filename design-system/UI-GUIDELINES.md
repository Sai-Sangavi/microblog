# Microblog UI guidelines

## Navigation and information architecture
- **Top bar only, no sidebar.** The product has five destinations, which fit one bar and keep the timeline the full-width focus.
- **Main sections, in order:** Home (`home`), Explore (`explore`), Messages (`messages`), Profile (`profile`), then Log out (`logout`). Search sits at the end of the bar as a field, not a section, because it is a tool rather than a place.
- **Signed-out visitors** see Home, Explore and Log in instead of Messages, Profile and Log out, because the other pages need an account.
- **Messages carries an unread `.badge-danger` count** shown only when above zero, so the bar stays quiet by default.
- **Below the tablet breakpoint** the links collapse behind a Menu button, because five links plus search do not fit a phone width.
- **Settings-style pages (edit profile, send message) are reached from Profile**, not the bar, because they are secondary tasks.

## Layout and density
- **Spacious single column**, capped at `size-container`, because posts are short text and read best at a narrow measure.
- **Page rhythm uses `.stack`** (`space-3` between posts, `stack-lg` between page sections) so spacing is never hand-set.
- **Primary breakpoint is tablet width (48rem).** Below it, everything is one column and controls keep `size-control` height; microblogging is mostly done on phones.
- **Pages show 25 posts, then Newer / Older posts as `.btn-secondary`**, matching the paginated feed and avoiding infinite scroll that hides the footer.

## Component usage
- **Post = `.card`** holding `.avatar`, author link, timestamp (`.text-muted .text-sm`) and body; stack posts with `.stack`. Each post is an independent unit, so a card, not a table row.
- **Messages inbox and follower lists = plain list** of `.cluster` rows with `.divider`, because the entries are uniform and need no card chrome.
- **No tables** anywhere in the product; there is no tabular data, and tables break on phones.
- **One `.btn-primary` per view** (Post, Save, Send); alternatives use `.btn-secondary`, Follow/Unfollow uses `.btn-secondary` / `.btn-ghost`, so the main action is unmistakable.
- **`.btn-danger` only for irreversible actions** (delete a post) and always behind a `.modal` confirm, to prevent accidental loss.
- **Forms use `.field` with `.input` / `.textarea`**; the post composer is a `.textarea` with a character hint in `.field-hint`, errors go in `.field-error` with `.is-invalid`, so the problem is next to the control.
- **Flashed server messages use `.alert`** at the top of content (info for confirmations, danger for failures), matching where users already look.
- **Background jobs (post export) show as an `.alert-info` with `.spinner`** until done, then a `.toast`, since the user may have navigated away.
- **Translate links and user hover previews use `.tooltip` / `.dropdown`**, never a new page, so reading flow is not interrupted.
- **Loading feed = `.skeleton` lines inside `.card`s; nothing to show = `.empty-state`** with a single action ("Follow someone on Explore"), so blank screens always explain themselves.
- **Filters or profile sub-views (Posts, Followers) use `.tabs`**; use `.accordion` only for help text, because content people need should not hide.

## Theme
- **Light only.** The token set defines one palette; a second theme would double review cost for a text-first product. All colors come from tokens, so dark can be added later by re-mapping them.

## Voice and tone
- **Friendly, brief, second person** ("Your post is live"), because the product is casual and posts are short.
- **Sentence case, verbs on buttons** ("Post", "Follow", "Send message"), never "Submit" or "OK".
- **Errors say what to do next**, not what broke ("Pick a different username"), and never blame the user.
- **Keep labels short and free of concatenated fragments**, because every string is translated.
