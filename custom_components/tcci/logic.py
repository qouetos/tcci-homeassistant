"""Calcul d'une nuit (portage de la page web : derive / normalize / stats).

Une "nuit D" = ligne de l'agenda = de D 20:00 a D+1 20:00 (heure locale).
Les heures sont en "minutes de grille" : 0 = 20:00 (D), 1440 = 20:00 (D+1).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, tzinfo


def win(d: date, tz: tzinfo) -> tuple[datetime, datetime]:
    start = datetime(d.year, d.month, d.day, 20, tzinfo=tz)
    nxt = d + timedelta(days=1)
    return start, datetime(nxt.year, nxt.month, nxt.day, 20, tzinfo=tz)


def current_night(now: datetime) -> date:
    return (now - timedelta(days=1)).date() if now.hour < 20 else now.date()


def gm(dt: datetime, d: date) -> int:
    return (dt.date() - d).days * 1440 + dt.hour * 60 + dt.minute - 1200


def fmt(g: float | None) -> str | None:
    if g is None:
        return None
    m = (round(g) + 1200) % 1440
    return f"{m // 60:02d}:{m % 60:02d}"


def empty_row() -> dict:
    return {"arrows": [], "segs": [], "s": [], "qs": "", "qr": "", "fj": "", "notes": "", "validated": False, "src": 0}


def normalize(r: dict) -> dict:
    r = {**empty_row(), **(r or {})}
    r["arrows"] = sorted(r["arrows"], key=lambda a: a["t"])
    r["s"] = sorted(r["s"])
    out: list[dict] = []
    for s in sorted((s for s in r["segs"] if s["b"] > s["a"]), key=lambda s: (s["a"], s["k"])):
        last = next((x for x in reversed(out) if x["k"] == s["k"]), None)
        if last and s["a"] <= last["b"]:
            last["b"] = max(last["b"], s["b"])
        else:
            out.append(dict(s))
    r["segs"] = out
    return r


def derive(events: list[dict], d: date, tz: tzinfo, settings: dict, now: datetime) -> dict:
    lat_bed = float(settings.get("latBed", 15)) * 60
    lat_re = float(settings.get("latResleep", 10)) * 60
    ws, we = (x.timestamp() for x in win(d, tz))
    nowts = now.timestamp()
    row = empty_row()
    g = lambda t: gm(datetime.fromtimestamp(t, tz), d)

    def seg(a, b):
        a, b = max(a, ws), min(b, we, nowts)
        if b - a >= 60:
            row["segs"].append({"a": g(a), "b": g(b), "k": "sleep"})

    in_bed = awake = False
    frm = None
    for e in sorted(events, key=lambda e: e["t"]):
        t, k = e["t"], e["k"]
        if t >= we:
            break
        in_w = t >= ws
        if in_w:
            row["src"] = max(row["src"], t)
        if k == "bed":
            if in_bed and not awake and frm is not None:
                seg(frm, t)
            in_bed, awake, frm = True, False, t + lat_bed
            if in_w:
                row["arrows"].append({"t": g(t), "d": "down"})
        elif k == "up":
            if in_bed and not awake and frm is not None:
                seg(frm, t)
            in_bed = awake = False
            frm = None
            if in_w:
                row["arrows"].append({"t": g(t), "d": "up"})
        elif k == "wake":
            if not in_bed:
                if in_w:
                    row["s"].append(g(t))
                continue
            if not awake and frm is not None:
                seg(frm, t)
            awake, frm = True, None
        elif k == "sleep":
            if in_bed:
                awake, frm = False, t + lat_re
        elif k == "s" and in_w:
            row["s"].append(g(t))
    if in_bed and not awake and frm is not None:
        seg(frm, we)
    return normalize(row)


def stats(r: dict) -> dict | None:
    sl = sorted((s for s in r["segs"] if s["k"] == "sleep"), key=lambda s: s["a"])
    iv: list[list[float]] = []
    opn = None
    for x in sorted(r["arrows"], key=lambda a: a["t"]):
        if x["d"] == "down":
            if opn is None:
                opn = x["t"]
        else:
            iv.append([opn if opn is not None else (min(sl[0]["a"], x["t"]) if sl else x["t"]), x["t"]])
            opn = None
    if opn is not None:
        iv.append([opn, max(opn, sl[-1]["b"] if sl else opn)])
    for s in sl:
        if not any(s["a"] < v[1] and s["b"] > v[0] for v in iv):
            iv.append([s["a"], s["b"]])
    iv.sort()
    blocks: list[list[float]] = []
    for v in iv:
        if blocks and v[0] - blocks[-1][1] < 120:
            blocks[-1][1] = max(blocks[-1][1], v[1])
        else:
            blocks.append(list(v))
    ov = lambda s, b: max(0, min(s["b"], b[1]) - max(s["a"], b[0]))
    main, best = None, -1
    for b in blocks:
        v = sum(ov(s, b) for s in sl)
        if v > best:
            best, main = v, b
    if not main or main[1] <= main[0]:
        return None
    m: list[dict] = []
    for s in sl:
        if not ov(s, main):
            continue
        c = {"a": max(s["a"], main[0]), "b": min(s["b"], main[1])}
        if m and c["a"] <= m[-1]["b"]:
            m[-1]["b"] = max(m[-1]["b"], c["b"])
        else:
            m.append(c)
    tst = sum(s["b"] - s["a"] for s in m)
    tib = main[1] - main[0]
    total = sum(s["b"] - s["a"] for s in sl)
    return {
        "bed": main[0], "up": main[1], "tib": tib, "tst": tst,
        "se": round(100 * tst / tib, 1) if tib else 0,
        "sol": m[0]["a"] - main[0] if m else None,
        "nwake": max(0, len(m) - 1),
        "waso": m[-1]["b"] - m[0]["a"] - tst if m else None,
        "nap": total - tst,
    }
