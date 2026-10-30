---
name: odoo-hours
description: Odoo hours, the user's timesheet in Odoo. Log or fill hours on the right contract with descriptions drawn from the day's git history; read how many hours a contract has or is missing; correct or delete entries. Use whenever the user mentions Odoo, logging hours or the timesheet.
allowed-tools: Bash(python3:*), Bash(git log:*), Bash(security add-generic-password:*)
---

# Odoo hours

Hours are rows of the `timesheet_entry` model of Odoo's Network Management
app (not the standard Timesheets app). `scripts/odoo_hours.py` talks to the
Odoo named in `~/.config/odoo-hours/config` over XML-RPC with the user's API
key.

```bash
H=~/.claude/skills/odoo-hours/scripts/odoo_hours.py
python3 $H contracts                      # active contracts and their monthly hours
python3 $H list [--from D --to D]         # entries, default this week
python3 $H month [--month YYYY-MM]        # hours per contract against its figures
python3 $H update <id> --desc "..." --dry-run   # also --contract, --start, --end
python3 $H add --contract acme --date 2026-10-28 --start 09:00 --end 12:00 --desc "Search results page" --dry-run
python3 $H delete <id>
```

Times on the command line are **local** (`ODOO_TZ`, else the computer's time
zone); the script converts to UTC, so pass them as the user says them.
`--contract` takes an id or a substring of the account, project or role of a
contract active on that date; the script refuses anything ambiguous and
prints the candidates.

When the script is not configured yet, or Odoo refuses the key (revoked or
expired), walk the user through [SETUP.md](SETUP.md); the new key comes from
them. When the script cannot reach Odoo, ask the user to connect the company
VPN and retry with the same configuration.

## Reading hours

"How many hours this month / how many are missing" is `month`: hours per
contract against the contract's monthly figure and, for a contract with a
daily maximum, against every weekday of the month at that figure (full time).
A contract active for part of the month shows its span instead of a monthly
delta. Which figure counts is in "Your rules". "What did I log this week / on
day X" is `list` with a range. Answer with the figures, in a short table when
there is more than one contract.

## Logging hours

1. **Contracts.** Run `contracts`; ids change, so read them each time. Route
   work to a contract with the table in "Your rules".

2. **The range.** `list` the days the user named. The rows already there are
   the schedule: many people create their blocks ahead with a placeholder
   description. A row with a placeholder or generic description gets
   `update`; `add` is for a day with no rows, in the user's standard day.
   Rows outside the range stay as they are.

3. **Evidence.** Unless the user already said what they did, gather the
   day's work: `git log --all --author=<name> --since=<day 00:00>
   --until=<day 23:59> --format='%ad %s' --date=iso` in the repos listed in
   "Your rules", plus what the current session built. Several checkouts of
   one repo (worktrees, clones) repeat its log: count each commit once.

4. **Descriptions the client can read.** These lines may end up on an
   invoice, so write each one as a plain phrase the client's engineer
   understands without knowing the codebase: the part of the product worked
   on and what it now does, in everyday words, in the register of "Your
   rules". Internal names stay out: repo, branch, issue number, commit
   prefix, tool or model names. One theme per block. A block with no commits
   of its own (reading, meetings, work that landed later) carries the
   previous block's description: the work continued, the log just does not
   show it.

   **Example.** Commits: "feat(search): rank results by recency (#231)",
   "fix(search): empty query no longer 500s (#240)". Description: "Search
   results ranking and fixes".

5. **Times.** Use what the user gives (dates, start/end or a total). With
   only a total, split it into the blocks of their standard day and say so.
   Keep a block on one day.

6. **Plan, confirm, write.** Run every `update` and `add` with `--dry-run`
   and show one table: date, time range, hours, contract, description before
   and after. These rows feed invoices; wait for the user's ok, then run the
   same commands without `--dry-run`. Done when `list` of the range shows
   every row with a readable description, no placeholder left, and the user
   has seen that list.

## Your rules (edit this section; it is yours)

Everything above is the same for everyone. What differs per person lives
here, and the agent reads it as fact. Replace the examples.

- **Standard day.** `09:00–12:00 and 13:00–18:00, 8 h`. "Log this week"
  means that schedule on every weekday of the range up to today; later
  dates only when I name them.
- **Monthly target.** `8 h on every weekday of the month.` Or: `The
  contract's monthly figure, no more.` Or: `Only the hours I actually
  worked; no target.` Whatever you agreed with your manager.
- **Repo → contract.** One row per repo family; add a row when a new repo
  appears.

  | Repos / work | Contract match |
  |---|---|
  | `~/Desktop/work/client-a-*`, client A meetings and demos | `client a` |
  | `~/Desktop/research-*`, research-team talks | `research` |

- **Description register.** `Plain English, 3–8 words.` Or point at a past
  week: `list --from ... --to ...` shows it.
- **Exceptions.** Anything the agent should ask about instead of fixing on
  its own, for example: `Rows on future dates are placeholders I keep on
  purpose; leave them. A month that does not match the target may be
  intended; ask before trimming or filling.`
