# Mac (KARAN) XFCE display-off power policy — verified 22 October 2026 IST

**Scope:** Automation workstream, owner-operated `mac-linux` on Linux Mint 22.3 XFCE 4.18.3, Generic Linux SSH three-lane bridge. Device power/display configuration only, no application code, worker, fan, root/sudo, credential or network changes. **Status: VERIFIED_LIVE for XFCE preferences and remote DPMS-off smoke test; reboot persistence and 2-minute natural idle expiration not tested.**

## Owner intent and safety

Keep plugged-in Mac awake for SSH/API/CLI development workloads while powering the display off after 2 idle minutes. Existing screen-lock controls are retained. Closing the lid still uses existing policy and may suspend: **do not claim safe closed-lid operation.** Graphical UI automation may require the desktop session to remain active/unlocked.

## Open Source / Reuse / Cost Gate

- Reused on-host `xfce4-power-manager` version 4.18.3, `xfconf-query`, `xset` and systemd; no new service, package, credential or paid API. Existing software source: https://github.com/xfce-mirror/xfce4-power-manager and https://docs.xfce.org/xfce/xfce4-power-manager/start.
- All work through existing paired owner-authenticated `mac-linux` operations/control lanes; no new bridge and no new OS account. No incremental software charge (ordinary existing electricity/network usage remains).
- Kept Light Locker enabled rather than weakening physical-access security.

## Baseline — 2026-10-22 02:04:25 IST

- Linux Mint 22.3, host `KARAN`, AC online, uptime ~15:29 hours; login session `karan` `c2` initially active XFCE X11 on display `:0`.
- `free -h`: RAM total 7.7 GiB, used 1.1 GiB, available 6.5 GiB; swap total 5.8 GiB, used ~372 MiB. `df -h /`: 111G volume, 53G used, 53G available, 50%.
- CPU 1-min load 0.07, package 49°C, applesmc `TC2C` 62°C, fan exhaust 3989 RPM. X11 DPMS **disabled**, XFCE presentation-mode **true**, existing X11 power-off timeout 600 s.
- Existing workers `generic-linux-automator`, `generic-linux-automator-lane@control`, `generic-linux-automator-lane@development` active. Baseline terminal receipt `f12d5e3c-9ad7-464f-9d21-13dbf5bd2860` exit 0; XFCE diagnosis receipt `b223c2a5-e9da-43b6-a98f-1713b75ce001` exit 0.

## Applied with backup

Original XFCE file copied with permissions preserved to:
`/home/karan/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-power-manager.pre-display-off-20261022.xml`.

Using `xfconf-query` in the existing `karan` DBus session:
- `/xfce4-power-manager/inactivity-on-ac = 0` (disable idle suspend on AC)
- `/xfce4-power-manager/blank-on-ac = 2` minutes
- `/xfce4-power-manager/dpms-on-ac-sleep = 1` minute (monitor power saving, not host suspend)
- `/xfce4-power-manager/dpms-on-ac-off = 2` minutes
- `/xfce4-power-manager/dpms-enabled = true`
- `/xfce4-power-manager/presentation-mode = false`

No battery-specific settings, lid actions, `systemd-logind`, SSH/sudo, browsers, or worker units changed. Write terminal receipt `9b38f149-60cf-4b89-83bb-76a8eab15019`, `completed`, exit 0; config readback exact. X11 `xset q` immediately showed DPMS enabled, standby 60 seconds, off 120 seconds.

## Verification / after — 2026-10-22 02:09:46–02:10:31 IST

- RAM total 7.7 GiB, used 1.1 GiB, available 6.5 GiB; swap used 372 MiB; disk remains 50%. Package temp **46°C** (down 3°C from baseline); `TC2C` 49°C; fan **3993 RPM** (up 4); 1-minute load **0.09** (was 0.07). Changes to temperature are short-term observations, not a demonstrated durable cooling effect.
- AC still online, uptime increased normally; all three worker services active and all three SSH lane heartbeats fresh. Comparison receipt `1514ef7d-444e-43bb-9759-854ddde07be6`, completed exit 0.
- An explicit 4-second X11 `xset dpms force off` test observed **Monitor is Off** while all three SSH services remained active and shell succeeded. Test trap then restored monitor **On**. Terminal receipt `07eba933-3e6d-4f55-80a1-ad3d0a803d3e` exit 0.
- **GUI limitation observed:** during display-off test `karan` session `c2` showed `Active=no, State=online`; later LightDM greeter `c3` was active, while all SSH workers remained active. Existing Light Locker security is preserved. No browser process was detected in sampled process list; live browser automation should not be assumed to work through a locked graphical session.
- No reboot test or full idle/locked-browser scenario was executed.

## Rollback

Use the same owner-authenticated lane and XFCE user DBus session, inspect current state before changing, then restore `presentation-mode=true`, and remove the five newly-created XFCE keys with `xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/<key> -r` (only after ensuring they were not subsequently modified intentionally). The timestamped original XML is retained for audit and selective restoration; do not overwrite a running xfconfd store or restart graphical login/worker services as a shortcut. Confirm `xset q`, SSH services, AC policy after rollback.

**STACK CHANGE:** Mac XFCE display-off after 120 s on AC, AC inactivity suspend disabled, 3-lane SSH retained; CLI smoke verified with screen off; GUI desktop locks; no closed-lid or reboot guarantee.
