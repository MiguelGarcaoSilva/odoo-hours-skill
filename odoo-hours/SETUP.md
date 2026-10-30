# Odoo hours: setup (once)

1. **Tell the script where Odoo is.** Create `~/.config/odoo-hours/config`
   with one line, the address you open in the browser:

   ```
   ODOO_URL=https://erp.example.com
   ```

   If the server hosts several databases, the script says so and asks for a
   second line, `ODOO_DB=<name>`. Times follow the computer's time zone; add
   `ODOO_TZ=<zone>` (e.g. `Europe/Paris`) to override it, which Windows
   needs. Environment variables of the same names also work and take
   precedence.

2. **Connect the company VPN.** Odoo is only reachable on the company
   network, same as in the browser; without the VPN the script stops with
   `cannot reach <your Odoo>`.

3. **Create your API key.** The key is personal and gives the script exactly
   your Odoo permissions.
   - If you sign in with Google and never set an Odoo password, set one
     first: sign out, open `$ODOO_URL/web/login`, click **Reset Password**,
     follow the link in the e-mail. Google sign-in keeps working; the
     password is only for the key dialog.
   - Open `$ODOO_URL/web?debug=1` (in older Odoo versions the API Keys
     section only shows in developer mode), then user menu → **Preferences**
     → **Account Security** → **New API Key**. Confirm with your Odoo
     password, name the key (for example `claude-code`), click **Generate
     key**, and copy it now: Odoo shows it only once.

4. **Store it.** On macOS, in the keychain, with your Odoo login as the
   account:

   ```bash
   security add-generic-password -a you@example.com -s odoo-api-key -w '<key>' -U
   ```

   On Linux or Windows, add two lines to the config file from step 1,
   `ODOO_LOGIN=you@example.com` and `ODOO_API_KEY=<key>`, and make it
   readable only by you: `chmod 600 ~/.config/odoo-hours/config` (the script
   warns if it is not). `ODOO_LOGIN` and `ODOO_API_KEY` in the environment
   work everywhere and take precedence. Keep the key out of chats and repos.

5. **Check.** `python3 ~/.claude/skills/odoo-hours/scripts/odoo_hours.py contracts`
   prints your active contracts. The first run may ask macOS to let `python3`
   read the keychain item; "Always allow" settles it.

To revoke a key: Preferences → Account Security → the trash icon next to it.
Then repeat steps 3 and 4; `-U` replaces the stored one.
