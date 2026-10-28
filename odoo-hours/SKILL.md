---
name: odoo-hours
description: Log the user's working hours in Odoo (the Network Management "Log Hours" model) on the right contract, at the times they say, with work descriptions drafted from the day's git history and session work; also read, summarize, fix and delete entries. Use whenever the user talks about logging, registering or putting in hours, in Portuguese or English ("loggar as horas", "registar horas", "meter as horas desta semana", "timesheet", "Odoo"), asks to fill a day, a week or a month on a contract, asks how many hours they have or how many are missing on a contract, or asks what they have logged or to correct a logged description, in any repo.
---

# Odoo hours

Hours are rows of the `timesheet_entry` model of Odoo's Network Management
app (not the standard Timesheets app). `scripts/odoo_hours.py` talks to the
Odoo named in `~/.config/odoo-hours/config` over XML-RPC with the user's API key,
read from the environment, the macOS keychain item `odoo-api-key`, or that
config file (see Setup). Plain `python3`, stdlib only.

```bash
H=~/.claude/skills/odoo-hours/scripts/odoo_hours.py
python3 $H contracts                      # active contracts and their monthly hours
python3 $H list [--from D --to D]         # entries, default this week
python3 $H month [--month YYYY-MM]        # hours per contract vs the contract's figures
python3 $H add --contract acme --date 2026-10-28 --start 09:00 --end 12:30 --desc "PDF reading in the design module" --dry-run
python3 $H update <id> --desc "..."     # also --contract, --start, --end, --dry-run
python3 $H delete <id>
```

Times on the command line are **local** (`ODOO_TZ`, default Europe/Lisbon);
the script converts to UTC, so never pre-convert. `--contract` takes an id or
a substring of the account, project or role of a contract active on that
date; the script refuses anything ambiguous and prints the candidates.

## Workflow for "log my hours"

1. **Contracts first.** Run `contracts`. Contracts change; never rely on
   remembered ids. Route work to a contract by account, using the table in
   "Your rules" below.

2. **Evidence before descriptions.** Unless the user already said what they
   did, gather the day's work yourself: `git log --author=<name>
   --since=<day 00:00> --until=<day 23:59> --format='%ad %s' --date=iso` in
   the repos listed in "Your rules", plus anything the current session built.

3. **Descriptions the client can read.** These lines may end up on an
   invoice, so write each one as a plain phrase the client's engineer
   understands without knowing the codebase: what part of the product was
   worked on and what it now does, in everyday words. Internal names stay
   out: no repo, branch, issue number, commit prefix, tool or model names.
   3–8 words, English. A block with no commits of its own (reading,
   meetings, work that landed later) carries the description of the
   previous block; never leave a block generic for lack of evidence.

   **Example.** Commits: "feat(search): rank results by recency (#231)",
   "fix(search): empty query no longer 500s (#240)". Description: "Search
   results ranking and fixes".

4. **Times.** Use what the user gives (dates, start/end or a total). With
   only a total, split it into the blocks of their standard day ("Your
   rules") and say so. Keep a block on one day. The script refuses an
   overlap with an existing entry, which usually means the hours are already
   logged (see 6).

5. **Plan, confirm, write.** Run every `add` with `--dry-run` first and show
   the plan as one table: date, time range, hours, contract, description.
   Wait for the user's ok, then run the same commands without `--dry-run`.
   These rows feed invoices; a confirm costs seconds, a wrong row costs a
   correction round with finance. After writing, run `list` for the range
   and show it.

6. **Days that already hold blocks get refined, not doubled.** Many people
   create their blocks in bulk with a placeholder description and refine
   later. On such a day the work is `update` on the existing rows, never a
   second set of entries. Show before/after with `--dry-run`, confirm,
   write. Rows outside the range the user named stay as they are.

## Reading hours

"How many hours this month / how many are missing" is `month`: it prints
hours per contract against the contract's monthly figure and, for a contract
with a daily maximum, against every weekday of the month at that figure.
"What did I log this week / on day X" is `list` with a range. Answer with the
figures, in a short table when there is more than one contract.

## Your rules (edit this section; it is yours)

Everything above is the same for everyone. What differs per person lives
here, and the agent reads it as fact. Replace the examples.

- **Standard day.** `09:00–12:00 and 13:00–18:00, 8 h`. "Log this week"
  means that schedule on every weekday of the range up to today, never into
  the future unless I name the dates.
- **Monthly target.** `8 h on every weekday of the month.` Or: `The
  contract's monthly figure, no more.` Or: `Only the hours I actually
  worked; no target.` Whatever you agreed with your manager.
- **Repo → contract.** One row per repo family; add a row when a new repo
  appears.

  | Repos / work | Contract match |
  |---|---|
  | `~/Desktop/work/client-a-*`, client A meetings and demos | `client a` |
  | `~/Desktop/research-*`, research-team talks | `research` |

- **Description register.** `Plain English, 3–8 words, one theme per
  block.` Or point at a past week: `list --from ... --to ...` shows it.
- **Exceptions.** Anything the agent should not "fix" on its own, for
  example: `Rows on future dates are placeholders I keep on purpose; leave
  them. A month that does not match the target may be intended; ask before
  trimming or filling.`

## Setup (once)

1. Tell the script where Odoo is: the file `~/.config/odoo-hours/config`
   with one line, `ODOO_URL=https://erp.example.com` (add `ODOO_DB=<name>`
   only if the script says the server hosts several databases).
   Environment variables of the same names also work and win.

2. In Odoo, open `<your Odoo>/web?debug=1`, then user menu → Preferences →
   Account Security → **New API Key** (the section only shows in debug
   mode). If you sign in with Google and have no Odoo password, set one
   first with the login page's "Reset Password" link; the key dialog asks
   for it.
3. Store the key once. macOS keychain, with your Odoo login as the account:

   ```bash
   security add-generic-password -a you@example.com -s odoo-api-key -w '<key>' -U
   ```

   Linux / Windows: two more lines in the config file from step 1,
   `ODOO_LOGIN=you@example.com` and `ODOO_API_KEY=<key>`, then `chmod 600` it. `ODOO_LOGIN` +
   `ODOO_API_KEY` in the environment work everywhere and take precedence.
4. `python3 ~/.claude/skills/odoo-hours/scripts/odoo_hours.py contracts`
   should print your active contracts.

If the script says Odoo refused the key, it was revoked or expired; mint a
new one, never search for an old one. If it says it cannot reach Odoo, the
usual cause is the company VPN being off; ask the user to connect it and
retry, rather than changing the configuration.
