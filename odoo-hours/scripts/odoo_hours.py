#!/usr/bin/env python3
"""Log and read your hours in Odoo (Network Management timesheet model).

Stdlib only. Times on the command line are local (Europe/Lisbon); Odoo stores UTC.

Configuration, from the environment or from ~/.config/odoo-hours/config (KEY=value lines):
  ODOO_URL      your Odoo address, e.g. https://erp.example.com   (required)
  ODOO_DB       the database name; only needed when the server has more than one
  ODOO_TZ       your local time zone, default Europe/Lisbon
  ODOO_LOGIN    your Odoo login (e-mail)
  ODOO_API_KEY  your API key
      macOS: both can come from the keychain item `odoo-api-key` instead
             (security add-generic-password -a <your e-mail> -s odoo-api-key -w <key> -U)
      Linux / Windows: put them in the config file and chmod 600 it

Needs Python 3.9+; on Windows also `pip install tzdata` for the time zone.

  contracts                      your active contracts (id, account, project, role, monthly hours)
  list [--from D] [--to D]       entries in a date range (default: this week)
  month [--month YYYY-MM]        hours per contract this month vs the contract's figures
  add --contract C --date D --start HH:MM (--end HH:MM | --hours H) --desc TEXT [--dry-run] [--force]
  update ID [--desc TEXT] [--contract C] [--start HH:MM] [--end HH:MM] [--dry-run]
  delete ID [ID ...]

`--contract` takes an id or a substring of the account / project / role of an
active contract (e.g. "acme"). One call = one entry, so a wrong line is one line.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import xmlrpc.client
from zoneinfo import ZoneInfo

CONFIG = os.path.expanduser("~/.config/odoo-hours/config")


def setting(name: str, default: str = "") -> str:
    """ODOO_* from the environment, else from ~/.config/odoo-hours/config (KEY=value lines)."""
    if os.environ.get(name, "").strip():
        return os.environ[name].strip()
    try:
        for line in open(CONFIG):
            k, _, v = line.partition("=")
            if k.strip() == name and v.strip():
                return v.strip().strip("'\"")
    except OSError:
        pass
    return default


URL = setting("ODOO_URL").rstrip("/")
if not URL:
    sys.exit(f"set ODOO_URL (your Odoo address), in the environment or as a KEY=value line in {CONFIG}")


def database() -> str:
    """ODOO_DB if set; else the server's only database; else ask for ODOO_DB."""
    db = setting("ODOO_DB")
    if db:
        return db
    try:
        names = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/db").list()
    except Exception as e:  # noqa: BLE001 - any transport or server error reads the same to the user
        sys.exit(f"cannot list databases at {URL} ({e}); set ODOO_DB")
    if len(names) == 1:
        return names[0]
    sys.exit(f"{URL} serves several databases, set ODOO_DB to one of: {', '.join(names) or 'none listed'}")


DB = database()
TZ = ZoneInfo(setting("ODOO_TZ", "Europe/Lisbon"))
ENTRY_FIELDS = ["start_time", "end_time", "duration_h", "contract", "work_description", "account", "project"]


# ---------------------------------------------------------------- connection
def credentials() -> tuple[str, str]:
    """(login, api_key): environment, else the macOS keychain item, else the config file."""
    login = os.environ.get("ODOO_LOGIN", "").strip()
    key = os.environ.get("ODOO_API_KEY", "").strip()
    if (not key or not login) and sys.platform == "darwin":
        try:
            meta = subprocess.run(["security", "find-generic-password", "-s", "odoo-api-key"],
                                  capture_output=True, text=True, check=True).stdout
            pw = subprocess.run(["security", "find-generic-password", "-s", "odoo-api-key", "-w"],
                                capture_output=True, text=True, check=True).stdout.strip()
            m = re.search(r'"acct"<blob>="([^"]+)"', meta)
            login = login or (m.group(1) if m else "")
            key = key or pw
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    if not key or not login:
        login = login or setting("ODOO_LOGIN")
        key = key or setting("ODOO_API_KEY")
        if key and os.path.exists(CONFIG) and os.name != "nt" and os.stat(CONFIG).st_mode & 0o077:
            print(f"warning: {CONFIG} holds your API key and is readable by others; chmod 600 it", file=sys.stderr)
    if not key or not login:
        sys.exit("no credentials: set ODOO_LOGIN and ODOO_API_KEY in the environment, or\n"
                 f"  macOS:  security add-generic-password -a <your e-mail> -s odoo-api-key -w <key> -U\n"
                 f"  other:  ODOO_LOGIN=... and ODOO_API_KEY=... lines in {CONFIG} (chmod 600)")
    return login, key


class Odoo:
    def __init__(self) -> None:
        self.login, self.key = credentials()
        self.uid = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common").authenticate(DB, self.login, self.key, {})
        if not self.uid:
            sys.exit(f"Odoo refused the API key for {self.login} (revoked or expired?)")
        self._obj = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

    def call(self, model: str, method: str, *args, **kw):
        return self._obj.execute_kw(DB, self.uid, self.key, model, method, list(args), kw)


# ---------------------------------------------------------------- time helpers
def to_utc(day: dt.date, hhmm: str) -> dt.datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    return dt.datetime.combine(day, dt.time(h, m), tzinfo=TZ).astimezone(dt.timezone.utc)


def odoo_str(t: dt.datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S")


def from_odoo(s: str) -> dt.datetime:
    return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=dt.timezone.utc).astimezone(TZ)


def parse_date(s: str | None) -> dt.date:
    if not s or s == "today":
        return dt.date.today()
    if s == "yesterday":
        return dt.date.today() - dt.timedelta(days=1)
    return dt.date.fromisoformat(s)


def weekdays(lo: dt.date, hi: dt.date) -> int:
    return sum(1 for i in range(max(0, (hi - lo).days + 1)) if (lo + dt.timedelta(i)).weekday() < 5)


# ---------------------------------------------------------------- contracts
def active_contracts(o: Odoo, on: dt.date | None = None) -> list[dict]:
    on = on or dt.date.today()
    rows = o.call(
        "contract", "search_read",
        [["network_member.user", "=", o.uid], ["active", "=", True],
         ["start_date", "<=", on.isoformat()], ["end_date", ">=", on.isoformat()]],
        fields=["account", "project", "job_role", "start_date", "end_date", "monthly_hours", "maximum_daily_hours"],
        order="start_date desc",
    )
    for r in rows:
        r["label"] = f"{r['account'][1]} / {r['project'][1]}"
    return rows


def resolve_contract(o: Odoo, spec: str, on: dt.date) -> dict:
    rows = active_contracts(o, on)
    if spec.isdigit():
        hits = [r for r in rows if r["id"] == int(spec)]
    else:
        s = spec.lower()
        hits = [r for r in rows if s in (r["label"] + " " + r["job_role"][1]).lower()]
    if len(hits) == 1:
        return hits[0]
    names = "\n".join(f"  {r['id']}  {r['label']}  ({r['start_date']} to {r['end_date']})" for r in rows)
    kind = "no active contract matches" if not hits else "ambiguous contract"
    sys.exit(f"{kind} {spec!r} on {on}. Active contracts:\n{names}")


# ---------------------------------------------------------------- commands
def cmd_contracts(o: Odoo, a) -> None:
    for r in active_contracts(o, parse_date(a.date)):
        print(f"{r['id']}  {r['label']}  | {r['job_role'][1]}  | {r['start_date']} to {r['end_date']}"
              f"  | {r['monthly_hours']} h/month, max {r['maximum_daily_hours']:g} h/day")


def entries_between(o: Odoo, start: dt.date, end: dt.date) -> list[dict]:
    lo = odoo_str(to_utc(start, "00:00"))
    hi = odoo_str(to_utc(end + dt.timedelta(days=1), "00:00"))
    return o.call(
        "timesheet_entry", "search_read",
        [["network_member_user_id", "=", o.uid], ["start_time", ">=", lo], ["start_time", "<", hi]],
        fields=ENTRY_FIELDS, order="start_time asc",
    )


def print_entries(rows: list[dict]) -> None:
    total = 0.0
    for e in rows:
        s, t = from_odoo(e["start_time"]), from_odoo(e["end_time"])
        total += e["duration_h"]
        print(f"{e['id']}  {s:%Y-%m-%d %a} {s:%H:%M}-{t:%H:%M}  {e['duration_h']:5.2f} h  "
              f"[{e['contract'][0]}] {e['account'][1] if e['account'] else '?'}  | {e['work_description'] or ''}")
    print(f"total {total:.2f} h over {len(rows)} entries")


def cmd_list(o: Odoo, a) -> None:
    today = dt.date.today()
    start = parse_date(a.frm) if a.frm else today - dt.timedelta(days=today.weekday())
    end = parse_date(a.to) if a.to else today
    print_entries(entries_between(o, start, end))


def cmd_month(o: Odoo, a) -> None:
    first = dt.date.fromisoformat(a.month + "-01") if a.month else dt.date.today().replace(day=1)
    last = (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    rows = entries_between(o, first, last)
    by: dict[int, float] = {}
    for e in rows:
        by[e["contract"][0]] = by.get(e["contract"][0], 0.0) + e["duration_h"]
    contracts = {r["id"]: r for r in active_contracts(o, first) + active_contracts(o, last)}
    today = dt.date.today()

    def figures(c: dict, hours: float) -> str:
        # Two references: the contract's monthly figure, and for a contract with a
        # daily maximum, every weekday of the month at that figure ("full time").
        # Which one your contract is measured against is between you and the account.
        out = f" / {c['monthly_hours']} h contract ({hours - c['monthly_hours']:+.1f})"
        if c["maximum_daily_hours"]:
            lo = max(first, dt.date.fromisoformat(c["start_date"]))
            hi = min(last, dt.date.fromisoformat(c["end_date"]))
            full = weekdays(lo, hi) * c["maximum_daily_hours"]
            due = weekdays(lo, min(hi, today)) * c["maximum_daily_hours"]
            out += f"; {full:.0f} h full time ({hours - full:+.1f}), {due:.0f} h due to date"
        return out

    for cid in sorted(set(by) | set(contracts)):
        c, hours = contracts.get(cid), by.get(cid, 0.0)
        label = c["label"] if c else f"contract {cid}"
        print(f"{cid}  {label}: {hours:.2f} h{figures(c, hours) if c else ''}")
    print(f"{first:%B %Y}: {sum(by.values()):.2f} h total")


def cmd_add(o: Odoo, a) -> None:
    day = parse_date(a.date)
    contract = resolve_contract(o, a.contract, day)
    start = to_utc(day, a.start)
    if a.end:
        end = to_utc(day, a.end)
    elif a.hours:
        end = start + dt.timedelta(hours=a.hours)
    else:
        sys.exit("give --end HH:MM or --hours H")
    if end <= start:
        sys.exit("end is not after start")
    hours = (end - start).total_seconds() / 3600
    same_day = entries_between(o, day, day)
    clash = [e for e in same_day
             if from_odoo(e["start_time"]) < end.astimezone(TZ) and from_odoo(e["end_time"]) > start.astimezone(TZ)]
    day_total = sum(e["duration_h"] for e in same_day if e["contract"][0] == contract["id"]) + hours
    plan = (f"{day:%Y-%m-%d %a} {start.astimezone(TZ):%H:%M}-{end.astimezone(TZ):%H:%M}  {hours:.2f} h  "
            f"[{contract['id']}] {contract['label']}  | {a.desc}")
    print(("DRY RUN  " if a.dry_run else "ADD      ") + plan)
    if clash:
        print("overlaps an existing entry:")
        print_entries(clash)
        if not a.force:
            sys.exit("refused; pass --force to log it anyway")
    if contract["maximum_daily_hours"] and day_total > contract["maximum_daily_hours"]:
        print(f"warning: {day_total:.2f} h on {day} exceeds the contract's {contract['maximum_daily_hours']:g} h/day")
    if a.dry_run:
        return
    new = o.call("timesheet_entry", "create", {
        "contract": contract["id"], "work_description": a.desc,
        "start_time": odoo_str(start), "end_time": odoo_str(end),
    })
    back = o.call("timesheet_entry", "read", [new], fields=ENTRY_FIELDS)[0]
    print(f"created {new}: {back['duration_h']:.2f} h on {back['account'][1] if back['account'] else '?'} / "
          f"{back['project'][1] if back['project'] else '?'}")


def cmd_update(o: Odoo, a) -> None:
    before = o.call("timesheet_entry", "read", [a.id], fields=ENTRY_FIELDS)[0]
    day = from_odoo(before["start_time"]).date()
    vals: dict = {}
    if a.desc is not None:
        vals["work_description"] = a.desc
    if a.contract:
        vals["contract"] = resolve_contract(o, a.contract, day)["id"]
    if a.start:
        vals["start_time"] = odoo_str(to_utc(day, a.start))
    if a.end:
        vals["end_time"] = odoo_str(to_utc(day, a.end))
    if not vals:
        sys.exit("nothing to change: give --desc, --contract, --start or --end")
    print("before:"); print_entries([before])
    if a.dry_run:
        print("DRY RUN would write", vals); return
    o.call("timesheet_entry", "write", [a.id], vals)
    print("after:"); print_entries(o.call("timesheet_entry", "read", [a.id], fields=ENTRY_FIELDS))


def cmd_delete(o: Odoo, a) -> None:
    rows = o.call("timesheet_entry", "read", a.ids, fields=ENTRY_FIELDS)
    print_entries(rows)
    o.call("timesheet_entry", "unlink", a.ids)
    print(f"deleted {len(rows)}")


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("contracts"); s.add_argument("--date", help="active on this day (default today)")
    s.set_defaults(fn=cmd_contracts)

    s = sub.add_parser("list"); s.add_argument("--from", dest="frm"); s.add_argument("--to")
    s.set_defaults(fn=cmd_list)

    s = sub.add_parser("month"); s.add_argument("--month", help="YYYY-MM (default current)")
    s.set_defaults(fn=cmd_month)

    s = sub.add_parser("add")
    s.add_argument("--contract", required=True, help="id or substring of account/project/role")
    s.add_argument("--date", default="today", help="YYYY-MM-DD, today, yesterday")
    s.add_argument("--start", required=True, help="HH:MM local time")
    s.add_argument("--end", help="HH:MM local time")
    s.add_argument("--hours", type=float, help="duration instead of --end")
    s.add_argument("--desc", required=True, help="work description")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--force", action="store_true", help="log even if it overlaps an existing entry")
    s.set_defaults(fn=cmd_add)

    s = sub.add_parser("update"); s.add_argument("id", type=int)
    s.add_argument("--desc"); s.add_argument("--contract"); s.add_argument("--start"); s.add_argument("--end")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_update)

    s = sub.add_parser("delete"); s.add_argument("ids", type=int, nargs="+")
    s.set_defaults(fn=cmd_delete)

    a = p.parse_args(argv)
    try:
        a.fn(Odoo(), a)
    except xmlrpc.client.Fault as e:
        sys.exit("Odoo error: " + e.faultString.strip().splitlines()[-1])
    except OSError as e:
        sys.exit(f"cannot reach {URL}: {e}")


if __name__ == "__main__":
    main()
