# Putting the tree on a private page

The output is static: `index.html`, `scans/`, `poster/` (the poster configurator) and the book PDF if
you made one. It works from a folder on disk, from a USB stick, or from any web server. The hard part is
keeping it private. Sizes: the page is the data and photos plus about 0.7 MB of Atlas 3D (three.js);
`poster/` is about 14 MB, almost all of it the three tree illustrations (`--no-posters` leaves it out).
The poster page reads `people.json` with `fetch`, so it needs a web server (or a local one, e.g.
`python3 -m http.server`); opened straight from disk it shows an error. The tree page itself works
from disk.

## Before anything leaves your computer

1. `publish.py out/tree.html publication/` — noindex, 11-digit numbers in the tree's data masked, scans
   copied, `poster/` written from the same published data (its `people.json` holds only names, surnames,
   years and parents).
   Add `--living 1926` (or another year) when the page will be seen by anyone outside the family the
   tree is about. Read the printed list of redacted people: someone with no birth year and no death
   counts as living only when a child or spouse does, so a childless person with no dates stays visible.
2. Living people: ask them before their names and dates go on any page, even a password-protected one.
3. Build the book from the published page: `build_book.py publication/index.html`, and every other
   book (one family's lines, the print edition) from the same page. The print edition (`--print`,
   `…-druk.pdf`) goes to the printer, not on the page: its page numbers replace the links.
4. Open `publication/index.html` and search for a few living people, a PESEL-like number and a note
   you know is sensitive. Open `poster/` and look for the same living people there.

## Access control

`<meta name="robots" content="noindex">` keeps honest search engines out; it doesn't keep anyone else
out. Pick one of these:

- **Send the folder, don't host it.** Zip `publication/` and send it. Nothing to configure.
- **HTTP basic authentication** on the folder (nginx `auth_basic`, Apache `.htaccess`, Caddy
  `basicauth`). One shared password for the family. Some phones show the login box badly; a small
  password form that sets a cookie is friendlier.
- **An access layer in front** (e.g. Cloudflare Access with one-time e-mail codes) when relatives
  should log in with their own e-mail.

An nginx sketch for a cookie gate: a form at `/private` posts to `/private/unlock`, which is behind
`auth_basic`; on success it sets a cookie, and the tree only answers when the cookie is there.

```nginx
map $cookie_tree_gate $gate_ok { default 0; "<long random token>" 1; }

location = /private/unlock {
    auth_basic "family";
    auth_basic_user_file /etc/nginx/tree.htpasswd;
    add_header Set-Cookie "tree_gate=<long random token>; Path=/; Secure; HttpOnly; SameSite=Lax";
    return 302 /drzewo/;
}
location ^~ /drzewo/ {
    if ($gate_ok = 0) { return 404; }          # without the cookie the path doesn't seem to exist
    add_header Cache-Control "private, no-store";
    add_header CDN-Cache-Control "no-store";
    add_header X-Robots-Tag "noindex, nofollow";
}
```

Keep the password and the token out of the repository that holds the site (a secret store, an
environment variable at deploy time).

## Caching

A CDN in front of the server may cache images and PDFs for days, and a cached response can go to a
visitor who never logged in. Send `Cache-Control: private, no-store` and `CDN-Cache-Control: no-store`
on the whole folder, then check from a shell with no cookie or password:

```
curl -sI https://example.org/drzewo/                 # 401 or 404
curl -sI https://example.org/drzewo/scans/x.jpg       # 401 or 404 too, also on a second request
```

## Updating

Rebuild, publish and copy the folder in one go (`build_tree.py` → `publish.py` → `build_book.py` →
`rsync -a --delete publication/ server:/…/drzewo/`). After a deploy, load the page logged in and check
that the new build is the one served: CSS and JS are inline, so one file decides it. The poster page
is several files (`poster/index.html`, `editor.js`, `poster.js`, `style.css`); a CDN that rewrites
cache headers on CSS and JS can serve an old one for a while after a deploy.

The access control above covers the whole folder, `poster/` included: its `people.json` is the
family's names.
