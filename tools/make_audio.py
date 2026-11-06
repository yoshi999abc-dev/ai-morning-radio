#!/usr/bin/env python3
"""台本（episodes/<日付>.json）から声（audio/<日付>.mp3）を作り、台本に時刻を埋める。

usage: python3 tools/make_audio.py [--voice ja-JP-NanamiNeural] [--rate +0%] [--force]

- 対象：episodes/YYYY-MM-DD.json のうち、まだ lines_timed がないもの（--force で全部作り直す）。
- 声：edge-tts（Microsoft Edge の読み上げ。APIキー不要）。1文ずつ作り、文の間に無音を入れて1本にする。
- 埋めるもの：seconds・lines_timed・segments・made_at（docs/formats.md の形）と episodes.json の一覧。
- 入れる無音：先頭 0.6 秒、文の間 0.25 秒、パートの間 1.05 秒、最後 2.05 秒
  （お手本の局 myradio の台本の時刻から割り出した値）。
- 要るもの：pip install edge-tts、ffmpeg。
"""
import argparse
import asyncio
import datetime
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EPISODES = ROOT / "episodes"
AUDIO = ROOT / "audio"
LIST = ROOT / "episodes.json"

LEAD, GAP_LINE, GAP_PART, TAIL = 0.6, 0.25, 1.05, 2.05
RATE_HZ = 24000
NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def lines_of(ep):
    """[(part, say, show), ...]。part は opening=0、news=1..N、closing=N+1。"""
    out = []
    for l in ep["opening"]:
        out.append((0, l["say"], l["show"]))
    for i, n in enumerate(ep["news"]):
        for l in n["lines"]:
            out.append((i + 1, l["say"], l["show"]))
    for l in ep["closing"]:
        out.append((len(ep["news"]) + 1, l["say"], l["show"]))
    return out


def check(ep, date):
    """台本の最低限の検査。足りなければ止める（声を作る前に）。"""
    for k in ("title", "opening", "closing", "news"):
        if not ep.get(k):
            die(f"{date}: '{k}' がありません")
    if ep.get("date") != date:
        die(f"{date}: 'date' が {ep.get('date')!r} です（ファイル名と合わせてください）")
    def line_ok(l):
        return isinstance(l, dict) and isinstance(l.get("say"), str) and l["say"].strip() \
            and isinstance(l.get("show"), str) and l["show"].strip()
    groups = [("opening", ep["opening"]), ("closing", ep["closing"])]
    for i, n in enumerate(ep["news"]):
        if not n.get("label") or not n.get("lines"):
            die(f"{date}: news[{i}] に label か lines がありません")
        if not str(n.get("url", "")).startswith("https://"):
            die(f"{date}: news[{i}] の url（出典）が https:// で始まっていません")
        groups.append((f"news[{i}].lines", n["lines"]))
    for name, ls in groups:
        for j, l in enumerate(ls):
            if not line_ok(l):
                die(f"{date}: {name}[{j}] は {{\"say\": …, \"show\": …}} の形で、空でない文字が要ります")


async def speak(text, voice, rate, path):
    import edge_tts
    last = None
    for attempt in range(3):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(str(path))
            if path.stat().st_size > 0:
                return
        except Exception as e:  # ネットワーク・サービスの一時的な失敗
            last = e
        time.sleep(2 * (attempt + 1))
    die(f"声を作れませんでした（3回失敗）: {text[:20]!r} … {last}")


def to_wav(src, dst):
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-ar", str(RATE_HZ), "-ac", "1",
                        "-c:a", "pcm_s16le", str(dst)], capture_output=True, text=True)
    if r.returncode:
        die(f"ffmpeg（wav 変換）が失敗しました: {r.stderr.strip()[:300]}")


def build(date, ep, voice, rate):
    check(ep, date)
    lines = lines_of(ep)
    AUDIO.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        out = wave.open(str(td / "all.wav"), "wb")
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(RATE_HZ)
        t = 0.0
        silent = lambda sec: out.writeframes(b"\x00\x00" * round(sec * RATE_HZ))
        timed, prev_part = [], None
        for k, (part, say, show) in enumerate(lines):
            asyncio.run(speak(say, voice, rate, td / f"{k}.mp3"))
            to_wav(td / f"{k}.mp3", td / f"{k}.wav")
            with wave.open(str(td / f"{k}.wav"), "rb") as w:
                if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE_HZ, 1, 2):
                    die("wav の形が想定と違います")
                frames = w.readframes(w.getnframes())
            gap = LEAD if prev_part is None else (GAP_PART if part != prev_part else GAP_LINE)
            silent(gap)
            t = round(t, 6) + gap
            dur = len(frames) / 2 / RATE_HZ
            out.writeframes(frames)
            timed.append({"start": round(t, 3), "end": round(t + dur, 3), "show": show, "part": part})
            t += dur
            prev_part = part
        silent(TAIL)
        t += TAIL
        out.close()
        mp3 = AUDIO / f"{date}.mp3"
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(td / "all.wav"), "-codec:a", "libmp3lame",
                            "-b:a", "64k", str(mp3)], capture_output=True, text=True)
        if r.returncode:
            die(f"ffmpeg（mp3 変換）が失敗しました: {r.stderr.strip()[:300]}")
    n_news = len(ep["news"])
    segs = []
    for part in range(n_news + 2):
        mine = [l for l in timed if l["part"] == part]
        nxt = [l for l in timed if l["part"] == part + 1]
        kind = "opening" if part == 0 else "closing" if part == n_news + 1 else "news"
        segs.append({"kind": kind, "index": part - 1 if kind == "news" else None,
                     "start": mine[0]["start"], "end": nxt[0]["start"] if nxt else round(t, 3)})
    ep.update({"format": "monoradio/news-1", "lang": "ja", "seconds": round(t, 2), "lines_timed": timed,
               "segments": segs, "made_at": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
               .strftime("%Y-%m-%dT%H:%M:%S")})
    return ep


def update_list(date, ep):
    items = json.loads(LIST.read_text(encoding="utf-8")) if LIST.exists() else []
    items = [e for e in items if e.get("date") != date]
    items.append({"date": date, "title": ep["title"], "seconds": ep["seconds"]})
    items.sort(key=lambda e: e["date"], reverse=True)
    LIST.write_text(json.dumps(items, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="ja-JP-NanamiNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--force", action="store_true", help="時刻のある台本も作り直す")
    a = ap.parse_args()
    if not shutil.which("ffmpeg"):
        die("ffmpeg が見つかりません")
    todo = []
    for p in sorted(EPISODES.glob("*.json")):
        if not NAME_RE.match(p.stem):
            continue
        ep = json.loads(p.read_text(encoding="utf-8"))
        if a.force or not ep.get("lines_timed"):
            todo.append((p, ep))
    if not todo:
        print("作る台本はありません")
        return
    for p, ep in todo:
        print(f"{p.stem}: 声を作ります（{sum(len(n['lines']) for n in ep.get('news', []))} 文のニュース）")
        ep = build(p.stem, ep, a.voice, a.rate)
        p.write_text(json.dumps(ep, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        update_list(p.stem, ep)
        print(f"{p.stem}: {ep['seconds']} 秒 → audio/{p.stem}.mp3")


if __name__ == "__main__":
    main()
