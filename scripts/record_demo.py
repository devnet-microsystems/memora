import asyncio
import json
import subprocess
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright
from PIL import Image, ImageDraw, ImageFont

BASE_URL = "http://127.0.0.1:5173"
API_BASE = "http://127.0.0.1:5001"
ROOT = Path("/Users/tonic/Lavori/NvidiaHackaton/scripts/demo_assets")
SCENES_DIR = ROOT / "scenes"
AUDIO_DIR = ROOT / "audio"
TITLES_DIR = ROOT / "title_cards"
SUBS_DIR = ROOT / "subtitles"
FINAL_MP4 = ROOT / "memora_demo_final.mp4"

SAY_VOICE = "Samantha"
NARRATION_RATE = 165

FAILURES = []
LOG = []


def log(msg):
    LOG.append(msg)
    print(msg)


def say(text, out_path, rate=NARRATION_RATE):
    subprocess.run(
        ["say", "-v", SAY_VOICE, "-r", str(rate), "-o", str(out_path),
         "--data-format=LEF32@32000", text],
        check=True, capture_output=True,
    )


def ffmpeg(args, check=True):
    result = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode(errors='replace')}")
    return result


def api_get(path):
    url = f"{API_BASE}{path}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        FAILURES.append(f"API GET {path}: {e}")
        return None


def api_post(path, body=None):
    url = f"{API_BASE}{path}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        FAILURES.append(f"API POST {path}: {e}")
        return None


def audio_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def make_title_card(text, subtext, out_path, duration_ms=4000):
    dur = duration_ms / 1000
    img = Image.new("RGB", (1920, 1080), (0x0B, 0x0E, 0x14))
    draw = ImageDraw.Draw(img)

    font_big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 84)
    font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)

    def center(font, t):
        bbox = draw.textbbox((0, 0), t, font=font)
        return (1920 - (bbox[2] - bbox[0])) // 2

    draw.text((center(font_big, text), 450), text, font=font_big, fill=(255, 255, 255))
    draw.text((center(font_sub, subtext), 590), subtext, font=font_sub, fill=(0x87, 0xE0, 0xC0))

    png = out_path.with_suffix(".png")
    img.save(str(png))

    ffmpeg([
        "-loop", "1", "-i", str(png),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-t", str(dur),
        str(out_path),
    ])


def make_subtitle(text, out_path):
    img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 40)

    bar_h = 110
    bar_y = 1080 - bar_h - 40
    draw.rectangle([0, bar_y, 1920, bar_y + bar_h], fill=(0, 0, 0, 170))

    words = text.split()
    lines = []
    cur = ""
    for w in words:
        trial = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] < 1700 or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)

    total_h = len(lines) * 52
    start_y = bar_y + (bar_h - total_h) // 2 + 10
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((1920 - w) // 2, start_y + i * 52), line, font=font, fill=(255, 255, 255))

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))


def overlay_subtitle(video_path, subtitle_path, output_path, start_sec, end_sec):
    ffmpeg([
        "-i", str(video_path),
        "-i", str(subtitle_path),
        "-filter_complex",
        (f"[0:v][1:v]overlay=0:main_h-overlay_h-40:enable='between(t,{start_sec},{end_sec})'[out]"),
        "-map", "[out]", "-map", "0:a?",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ])


async def wait_ms(page, ms):
    await page.wait_for_timeout(ms)


async def highlight_and_click(page, selector, label, index=0):
    locator = page.locator(selector)
    count = await locator.count()
    if count == 0:
        FAILURES.append(f"UI element not found: {selector} ({label})")
        return None
    target = locator.nth(index) if count > 1 else locator.first
    await target.highlight()
    await wait_ms(page, 500)
    await target.click()
    await wait_ms(page, 1000)
    return target


async def record_scene(browser, name, url_path, actions, hold_ms):
    log(f"  Recording: {name} -> {url_path}")
    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        record_video_dir=str(SCENES_DIR),
        record_video_size={"width": 1920, "height": 1080},
    )
    page = await context.new_page()
    page.set_default_timeout(10000)
    await page.goto(f"{BASE_URL}{url_path}", wait_until="networkidle", timeout=20000)
    await wait_ms(page, 1200)

    if actions:
        for action in actions:
            await action(page)

    await wait_ms(page, hold_ms)
    video_path = await page.video.path()
    await context.close()
    log(f"  Done: {name}")
    return video_path


async def main():
    for d in (SCENES_DIR, AUDIO_DIR, TITLES_DIR, SUBS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log("MEMORA Demo Video Recording - Starting")
    log("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--autoplay-policy=no-user-gesture-required"],
        )

        try:
            # ================================================================
            # TITLE CARDS
            # ================================================================
            log("[1/17] Title cards...")
            make_title_card(
                "MEMORA",
                "Private AI Companion for MCI Patients & Caregivers",
                TITLES_DIR / "title1.mp4",
                4000,
            )
            make_title_card(
                "Nebius x NVIDIA Global AI Hackathon",
                "Personal AI Track",
                TITLES_DIR / "title2.mp4",
                4000,
            )
            log("[1/17] Title cards done")

            # ================================================================
            # SCENE 2: Patient greeting
            # ================================================================
            log("[2/17] Patient greeting...")
            patient_greeting_video = await record_scene(
                browser, "patient_greeting", "/patient",
                None,
                8000,
            )

            # ================================================================
            # SCENE 3: AAC - I'm thirsty
            # ================================================================
            log("[3/17] AAC: I'm thirsty...")
            async def aac_thirsty(page):
                await highlight_and_click(page, "#aac-grid .btn-aac", "I'm thirsty", 0)
            aac_thirsty_video = await record_scene(
                browser, "aac_thirsty", "/patient",
                [aac_thirsty],
                9000,
            )

            # ================================================================
            # SCENE 4: AAC - Medicine?
            # ================================================================
            log("[4/17] AAC: Medicine?...")
            async def aac_medicine(page):
                await highlight_and_click(page, "#aac-grid .btn-aac", "Medicine?", 1)
            aac_medicine_video = await record_scene(
                browser, "aac_medicine", "/patient",
                [aac_medicine],
                9000,
            )

            # ================================================================
            # SCENE 5: AAC - Bathroom
            # ================================================================
            log("[5/17] AAC: Bathroom...")
            async def aac_bathroom(page):
                await highlight_and_click(page, "#aac-grid .btn-aac", "Bathroom", 2)
            aac_bathroom_video = await record_scene(
                browser, "aac_bathroom", "/patient",
                [aac_bathroom],
                7000,
            )

            # ================================================================
            # SCENE 6: AAC - Call family
            # ================================================================
            log("[6/17] AAC: Call family...")
            async def aac_family(page):
                await highlight_and_click(page, "#aac-grid .btn-aac", "Call family", 3)
            aac_family_video = await record_scene(
                browser, "aac_family", "/patient",
                [aac_family],
                7000,
            )

            # ================================================================
            # SCENE 7: SOS
            # ================================================================
            log("[7/17] SOS button...")
            async def sos_action(page):
                await highlight_and_click(page, "#btn-sos", "SOS button")
            sos_video = await record_scene(
                browser, "sos", "/patient",
                [sos_action],
                13000,
            )

            # ================================================================
            # SCENE 8: Pill repetition x3
            # ================================================================
            log("[8/17] Pill repetition x3...")
            async def pill_repetition(page):
                for i in range(3):
                    await highlight_and_click(page, "#aac-grid .btn-aac", "Medicine?", 1)
                    await wait_ms(page, 1500)
            pill_video = await record_scene(
                browser, "pill_repetition", "/patient",
                [pill_repetition],
                16000,
            )

            # Verifica API: anomalia
            memory = api_get("/api/memory")
            anomaly_found = False
            if memory:
                for n in memory.get("nodes", []):
                    if n.get("group") == "alert" and "anomal" in (n.get("label") or "").lower():
                        anomaly_found = True
                        break
            if not anomaly_found:
                FAILURES.append("No anomaly alert detected after 3x pill question via API")

            # ================================================================
            # SCENE 9: Transition to caregiver
            # ================================================================
            log("[9/17] Transition to caregiver...")
            async def go_caregiver(page):
                await page.click('a:has-text("Caregiver Dashboard")')
            transition_video = await record_scene(
                browser, "transition", "/patient",
                [go_caregiver],
                3000,
            )

            # ================================================================
            # SCENE 10: Caregiver alert
            # ================================================================
            log("[10/17] Caregiver alert...")
            async def caregiver_alert(page):
                await highlight_and_click(page, 'button:has-text("Alerts")', "Alerts section")
            caregiver_alert_video = await record_scene(
                browser, "caregiver_alert", "/caregiver",
                [caregiver_alert],
                9000,
            )

            memory2 = api_get("/api/memory")
            alert_found = False
            alert_id = None
            if memory2:
                for n in memory2.get("nodes", []):
                    if n.get("group") == "alert" and n.get("status") != "acknowledged":
                        alert_found = True
                        alert_id = n.get("id")
                        break
            if not alert_found:
                FAILURES.append("No open alert found on caregiver dashboard via API")

            # ================================================================
            # SCENE 11: Acknowledge alert
            # ================================================================
            log("[11/17] Acknowledge alert...")
            async def ack_alert(page):
                await highlight_and_click(page, 'button:has-text("Acknowledge")', "Acknowledge alert", 0)
            ack_video = await record_scene(
                browser, "ack_alert", "/caregiver",
                [ack_alert],
                7000,
            )

            if alert_id:
                alert_detail = api_get(f"/api/alerts/{alert_id}")
                if alert_detail and alert_detail.get("status") != "acknowledged":
                    FAILURES.append(f"Alert {alert_id} not acknowledged after UI action")

            # ================================================================
            # SCENE 12: Memory Graph
            # ================================================================
            log("[12/17] Memory Graph...")
            async def show_graph(page):
                await highlight_and_click(page, 'button:has-text("Memory Graph")', "Memory Graph", 0)
            graph_video = await record_scene(
                browser, "memory_graph", "/caregiver",
                [show_graph],
                9000,
            )

            # ================================================================
            # SCENE 13: Medications (Ramipril & Atorvastatin)
            # ================================================================
            log("[13/17] Medications...")
            async def show_meds(page):
                await highlight_and_click(page, 'button:has-text("Medications")', "Medications section", 0)
            meds_video = await record_scene(
                browser, "medications", "/caregiver",
                [show_meds],
                9000,
            )

            # Verifica API farmaci su DB inglese (porta 8000, backend usato dalla UI)
            import urllib.request as _urllib
            import os as _os
            try:
                _memora_key = _os.getenv("MEMORA_API_KEY", "")
                _req = _urllib.Request("http://127.0.0.1:8000/med/status",
                                       headers={"X-Memora-Key": _memora_key})
                with _urllib.urlopen(_req, timeout=10) as _r:
                    _meds_data = _urllib.json.loads(_r.read().decode())
                _med_ids = {m["id"] for m in _meds_data.get("meds", [])}
                if "med_ramipril" not in _med_ids:
                    FAILURES.append("med_ramipril not found in /med/status (DB inglese)")
                if "med_atorvastatin" not in _med_ids:
                    FAILURES.append("med_atorvastatin not found in /med/status (DB inglese)")
                for m in _meds_data.get("meds", []):
                    if m["id"] == "med_ramipril" and "2.5 mg" not in m.get("content", ""):
                        FAILURES.append("Ramipril dosage non corretto")
                    if m["id"] == "med_atorvastatin" and "10 mg" not in m.get("content", ""):
                        FAILURES.append("Atorvastatin dosage non corretto")
            except Exception as _e:
                FAILURES.append(f"Verifica farmaci DB inglese fallita: {_e}")

            # ================================================================
            # SCENE 14: Voice Memory
            # ================================================================
            log("[14/17] Voice Memory flow...")
            async def voice_memory_flow(page):
                await highlight_and_click(page, 'button:has-text("Add memory by voice")', "Voice Memory button")
                await wait_ms(page, 1000)

                await page.evaluate("""() => {
                    const ta = document.getElementById('voice-preview-text');
                    if (ta) {
                        ta.value = 'Maria prefers tea after her morning walk.';
                        ta.dispatchEvent(new Event('input', { bubbles: true }));
                    }
                }""")
                await wait_ms(page, 800)

                await highlight_and_click(page, 'button:has-text("Extract facts")', "Extract facts", 0)
                await wait_ms(page, 1500)

                await highlight_and_click(page, 'button:has-text("Save")', "Save facts", 0)
                await wait_ms(page, 1000)

            voice_video = await record_scene(
                browser, "voice_memory", "/caregiver",
                [voice_memory_flow],
                20000,
            )

            memory3 = api_get("/api/memory")
            fact_saved = False
            if memory3:
                for n in memory3.get("nodes", []):
                    if "tea" in (n.get("label") or "").lower() and n.get("group") != "alert":
                        fact_saved = True
                        break
            if not fact_saved:
                FAILURES.append("No tea preference fact found in memory after Voice Memory save")

            # ================================================================
            # SCENE 15: Life Book
            # ================================================================
            log("[15/17] Life Book...")
            life_book_video = await record_scene(
                browser, "life_book", "/story",
                None,
                16000,
            )

            today = api_get("/api/today?patient_id=patient_alex&lang=en")
            if not today:
                FAILURES.append("Life Book /api/today returned no data")

            # ================================================================
            # SCENE 16: Judges
            # ================================================================
            log("[16/17] Judges...")
            judges_video = await record_scene(
                browser, "judges", "/judges",
                None,
                13000,
            )

            # ================================================================
            # SCENE 17: Closing
            # ================================================================
            log("[17/17] Closing...")
            closing_video = await record_scene(
                browser, "closing", "/judges",
                None,
                7000,
            )

            await browser.close()
            log("[16/17] All scenes recorded")

        except Exception as e:
            await browser.close()
            raise

    # ========================================================================
    # NARRATION AUDIO + SUBTITLES
    # ========================================================================
    log("Generating narration audio and subtitles...")
    narrations = [
        ("title1", "Memora is a private, persistent AI companion for people with mild cognitive impairment and their caregivers.", TITLES_DIR / "title1.mp4"),
        ("title2", "Nebius x NVIDIA Global AI Hackathon. Personal AI Track.", None),
        ("patient_greeting", "Meet Maria. Every morning, Memora greets her with today's schedule and medication reminders.", None),
        ("aac_thirsty", "For patients with aphasia, AAC buttons let them communicate needs instantly. I'm thirsty.", None),
        ("aac_medicine", "Medicine? Memora shows the schedule and confirms intake.", None),
        ("aac_bathroom", "Bathroom. Simple, immediate, no typing required.", None),
        ("aac_family", "Call family. Connects Maria with her daughter Giulia right away.", None),
        ("sos", "In an emergency, SOS sends an instant alert to the caregiver—no LLM delay.", None),
        ("pill_repetition", "Repeated questions are detected automatically. Did I take my pill? Did I take my pill? Did I take my pill?", None),
        ("transition", "The caregiver dashboard sees everything, in real time.", None),
        ("caregiver_alert", "A new alert appears immediately—no refresh needed.", None),
        ("ack_alert", "The caregiver acknowledges the alert, and the patient sees confirmation.", None),
        ("memory_graph", "The memory graph visualizes people, places, medications, and their relationships.", None),
        ("medications", "The Caregiver dashboard shows today's medications: Ramipril 2.5 mg at 9 AM for hypertension, and Atorvastatin 10 mg at 8 PM for dyslipidemia. All demo data is clearly marked fictional.", None),
        ("voice_memory", "Voice memory lets caregivers add facts by speaking. Every fact is transcribed, previewed, and reviewed before it is saved.", None),
        ("life_book", "The Life Book gives Maria a personalized daily schedule, people, places, medications, and stories.", None),
        ("judges", "Judges: FastAPI backend, Flask dashboard, NetworkX memory graph, Nebius Token Factory, Tavily local search, PII redaction, and deterministic anomaly detection.", None),
        ("closing", "Memora. Private, persistent, privacy-first. Built for the vulnerable, not the viral.", TITLES_DIR / "title2.mp4"),
    ]

    audio_map = {}
    sub_map = {}
    for key, text, _ in narrations:
        audio_path = AUDIO_DIR / f"narration_{key}.m4a"
        say(text, audio_path)
        audio_map[key] = audio_path

        sub_path = SUBS_DIR / f"sub_{key}.png"
        make_subtitle(text, sub_path)
        sub_map[key] = sub_path

    # ========================================================================
    # COMBINE SCENES
    # ========================================================================
    log("Combining scenes with subtitles and audio...")
    scenes = [
        (TITLES_DIR / "title1.mp4", "title1", "title1", 4.0),
        (TITLES_DIR / "title2.mp4", "title2", "title2", 4.0),
        (patient_greeting_video, "patient_greeting", "patient_greeting", 8.0),
        (aac_thirsty_video, "aac_thirsty", "aac_thirsty", 9.0),
        (aac_medicine_video, "aac_medicine", "aac_medicine", 9.0),
        (aac_bathroom_video, "aac_bathroom", "aac_bathroom", 7.0),
        (aac_family_video, "aac_family", "aac_family", 7.0),
        (sos_video, "sos", "sos", 13.0),
        (pill_video, "pill_repetition", "pill_repetition", 16.0),
        (transition_video, "transition", "transition", 3.0),
        (caregiver_alert_video, "caregiver_alert", "caregiver_alert", 9.0),
        (ack_video, "ack_alert", "ack_alert", 7.0),
        (graph_video, "memory_graph", "memory_graph", 9.0),
        (meds_video, "medications", "medications", 9.0),
        (voice_video, "voice_memory", "voice_memory", 20.0),
        (life_book_video, "life_book", "life_book", 16.0),
        (judges_video, "judges", "judges", 13.0),
        (closing_video, "closing", "closing", 7.0),
    ]

    scene_files = []
    for i, (video_path, audio_key, sub_key, duration_sec) in enumerate(scenes):
        log(f"  Processing scene {i+1}/{len(scenes)}: {audio_key}")
        audio_path = audio_map[audio_key]
        sub_path = sub_map[sub_key]

        with_sub = ROOT / f"tmp_sub_{i:02d}.mp4"
        adur = audio_duration(audio_path)
        overlay_subtitle(
            video_path, sub_path, with_sub,
            start_sec=0.5, end_sec=min(adur, duration_sec),
        )

        scene_out = ROOT / f"scene_{i:02d}.mp4"
        ffmpeg([
            "-i", str(with_sub),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(scene_out),
        ])
        scene_files.append(scene_out)
        try:
            with_sub.unlink()
        except Exception:
            pass

    # ========================================================================
    # FINAL CONCAT
    # ========================================================================
    log("Encoding final MP4...")
    concat_list = ROOT / "concat.txt"
    concat_list.write_text("\n".join(f"file '{f}'" for f in scene_files) + "\n")

    ffmpeg([
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(FINAL_MP4),
    ])

    # Verifica finale
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate",
         "-show_entries", "format=duration,size",
         "-of", "csv=p=0", str(FINAL_MP4)],
        capture_output=True, text=True,
    )
    log(f"\nFinal probe: {result.stdout.strip()}")

    size_mb = FINAL_MP4.stat().st_size / 1024 / 1024
    dur_sec = audio_duration(FINAL_MP4)
    log(f"\nDone! Final video: {FINAL_MP4}")
    log(f"Duration: {dur_sec:.1f}s ({dur_sec/60:.1f} min)")
    log(f"Size: {size_mb:.1f} MB")

    if FAILURES:
        log("\n--- ISSUES DETECTED (not simulated) ---")
        for f in FAILURES:
            log(f"  - {f}")
    else:
        log("\nAll API and UI verifications passed.")


if __name__ == "__main__":
    asyncio.run(main())
