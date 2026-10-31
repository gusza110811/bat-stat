#!/usr/bin/env python3
"""
Battery → Discord webhook reporter.

Usage:
    python battery_webhook.py <discord_webhook_url>

Behavior:
  * Sends a status message immediately on startup.
  * While running on battery power: sends a status message every 10 seconds.
  * While plugged in: stays silent, EXCEPT when the battery transitions
    from <95% to >=95% (i.e. "charged to >95%").
"""

import sys
import time

import psutil
import requests

INTERVAL = 60          # seconds between polls
CHARGE_THRESHOLD = 95  # ">95%"


# --------------------------------------------------------------------------- #
# Battery helpers
# --------------------------------------------------------------------------- #
def get_battery():
    """Return the battery namedtuple, or None if no battery is available."""
    try:
        return psutil.sensors_battery()
    except Exception as e:
        print(f"[warn] could not read battery: {e}", file=sys.stderr)
        return None


def format_status(bat):
    if bat is None:
        return "⚠️ **No battery detected** (or battery info is unavailable on this system)."

    state = "🔌 Plugged in / charging" if bat.power_plugged else "🔋 Running on battery"

    secs = bat.secsleft
    if secs == getattr(psutil, "POWER_TIME_UNLIMITED", -2):
        timeleft = "unlimited (plugged in)"
    elif secs is None or secs < 0:
        timeleft = "unknown"
    else:
        h, m = divmod(secs // 60, 60)
        timeleft = f"{h}h {m:02d}m"

    return (
        f"{state}\n"
        f"Battery: **{bat.percent}%**\n"
        f"Time remaining: {timeleft}"
    )


# --------------------------------------------------------------------------- #
# Webhook
# --------------------------------------------------------------------------- #
def send(webhook_url, content):
    try:
        r = requests.post(webhook_url, json={"content": content}, timeout=10)
        r.raise_for_status()
        print(f"[sent] {content.splitlines()[0]}")
    except Exception as e:
        print(f"[error] failed to send webhook: {e}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    if len(sys.argv) < 2:
        print("Usage: python battery_webhook.py <discord_webhook_url>", file=sys.stderr)
        sys.exit(1)

    webhook_url = sys.argv[1]

    # --- startup message ---------------------------------------------------
    bat = get_battery()
    send(webhook_url, "**Battery Monitor started**\n" + format_status(bat))

    # Track whether we were already above the threshold, so the ">95%"
    # notification fires only on a transition.
    was_above = bat is not None and bat.percent >= CHARGE_THRESHOLD

    # --- main loop ---------------------------------------------------------
    while True:
        time.sleep(INTERVAL)

        bat = get_battery()
        if bat is None:
            continue

        on_battery = not bat.power_plugged
        above = bat.percent >= CHARGE_THRESHOLD

        send_it = False
        reason = ""

        if on_battery:
            send_it = True
            reason = "Periodic update (on battery)"
        elif above and not was_above:
            send_it = True
            reason = f"Battery charged above {CHARGE_THRESHOLD}%"

        if send_it:
            send(webhook_url, f"**{reason}**\n" + format_status(bat))

        was_above = above


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
