# odoo-hours

A Claude Code skill that logs your hours in Odoo from the terminal: the
right contract, the times you say, and a work description drafted from your
day's git history. It also reads what you logged and fixes it.

Odoo versions before 20 have no MCP server, so the skill talks to
Odoo's XML-RPC API with a personal API key. Stdlib Python 3.9+, nothing to
install (Windows needs `pip install tzdata` for the time zone). Runs on
macOS, Linux and Windows; only where the key is stored differs.

**Compatibility.** The script writes the `timesheet_entry` model of the
Network Management app (contracts, accounts, principals). It does not drive
the standard Odoo Timesheets app (`account.analytic.line`); that would be a
second small backend if anyone needs it.

## Install

```bash
git clone <this repo>
cp -r odoo-hours-skill/odoo-hours ~/.claude/skills/odoo-hours
```

Then tell it where your Odoo is: create the file `~/.config/odoo-hours/config`
with one line, the address you open in the browser:

```
ODOO_URL=https://erp.example.com
```

That is all for most servers. If yours hosts several databases, the script
says so and asks for a second line, `ODOO_DB=<name>`. Environment variables
of the same names also work and take precedence.

## Create your API key (once)

The key is personal and gives the script exactly your Odoo permissions.

1. **If you sign in with Google and never set an Odoo password**, set one
   first: sign out, open `$ODOO_URL/web/login`, click **Reset Password**,
   enter your e-mail, follow the link in the e-mail. Google sign-in keeps
   working; the password is only for step 3.
2. Open `$ODOO_URL/web?debug=1`. The `debug=1` part matters: in older Odoo versions the
   API Keys section only shows in developer mode.
3. User menu (top right) → **Preferences** → tab **Account Security** →
   **New API Key**. Confirm with your Odoo password, give the key a name
   (for example `claude-code`), click **Generate key**. Copy it now: Odoo
   shows it only once.
4. Store it. On **macOS**, in the keychain, with your Odoo login as the
   account:

   ```bash
   security add-generic-password -a you@example.com -s odoo-api-key -w '<key>' -U
   ```

   On **Linux or Windows**, add two lines to the config file from Install,
   so it reads:

   ```
   ODOO_URL=https://erp.example.com
   ODOO_LOGIN=you@example.com
   ODOO_API_KEY=<key>
   ```

   and make it readable only by you: `chmod 600 ~/.config/odoo-hours/config`
   (the script reminds you if it is not).

   Environment variables `ODOO_LOGIN` and `ODOO_API_KEY` work everywhere
   and take precedence. Never paste the key into a chat or a file in a repo.
5. Check:

   ```bash
   python3 ~/.claude/skills/odoo-hours/scripts/odoo_hours.py contracts
   ```

   It prints your active contracts. The first run may ask macOS to let
   `python3` read the keychain item; "Always allow" settles it.

To revoke a key: Preferences → Account Security → the trash icon next to it.
Then repeat steps 3 and 4; `-U` replaces the stored one.

## Make it yours

Open `~/.claude/skills/odoo-hours/SKILL.md` and edit the section
**Your rules**: your standard day, how your monthly target works, which
repos map to which contract, how you like descriptions written, and anything
the agent should ask about instead of fixing. The rest of the file is shared
behaviour and should not need changes. Your copy is local; this repo keeps
the neutral version.

## Use

In any Claude Code session:

- "Log this week's hours on the Acme contract, 8 hours a day, 9 to 12 and
  13 to 18, one general description per day." The agent lists your
  contracts, reads your commits per day, drafts one plain description per
  block, shows you the plan, and writes after your ok.
- "Put 2 hours yesterday at 20:00 on research, prompt optimization."
- "How many hours do I have this month? How many are missing on research?"
- "Change Tuesday's description to PDF reading in the design module."
- "What did I log last week?"

### Example session

> **You:** log this week's hours on the Acme contract, 9 to 12 and 13 to 18, one plain description per block from what I committed
>
> **Claude:** Acme resolves to contract 1042 (Acme / Website Redesign). Monday to Wednesday already hold those blocks with a placeholder description, so this is an update, not new rows. From your commits:
>
> | Day | Block | Now | Proposed |
> |---|---|---|---|
> | Mon 26 | 09–12 | todo | Search results page |
> | Mon 26 | 13–18 | todo | Search filters and sorting |
> | Tue 27 | 09–12 | todo | Checkout form validation |
> | Tue 27 | 13–18 | todo | Order confirmation e-mails |
> | Wed 28 | 09–12 | todo | Product page performance |
> | Wed 28 | 13–18 | todo | Image loading on mobile |
>
> Hours and contract unchanged. Say "ok" and I write the six, or correct any line first.
>
> **You:** ok
>
> **Claude:** Written and read back; the week now shows the six descriptions above, 24 h on Acme.

> **You:** how many hours am I missing on research this month?
>
> **Claude:** Research: 12 h logged of 20 h on the contract, 8 h missing. Acme: 96 h logged, 96 h due to date.

Or straight from the shell:

```bash
H=~/.claude/skills/odoo-hours/scripts/odoo_hours.py
python3 $H contracts
python3 $H list --from 2026-10-19 --to 2026-10-25
python3 $H month --month 2026-10
python3 $H add --contract acme --date 2026-10-28 --start 09:00 --end 12:00 --desc "Reading customer specification tables" --dry-run
python3 $H update <id> --desc "Product page performance"
python3 $H delete <id>
```

Times are local (`ODOO_TZ`, default Europe/Lisbon). `add` refuses to
overlap an existing entry unless you pass `--force`, and `--dry-run` shows
what would be written without writing it.

## Good to know

- Only `contract`, `work_description`, `start_time` and `end_time` are
  written; account, project and principal derive from the contract.
- `month` prints two references: the contract's monthly figure, and for a
  contract with a daily maximum, every weekday of the month at that figure.
  Which one applies to you is between you and whoever manages the account.
- The key is yours; the script never writes it anywhere. Revoke it in Odoo
  under Preferences → Account Security whenever you want.
