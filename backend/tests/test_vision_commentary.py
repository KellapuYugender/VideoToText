import threading
import time
from collections import Counter

import numpy as np

from vision.commentary import CommentaryFeed, build_prompt, clean_line, clean_sport
from vision.events import Event
from vision.source import Frame


def frame(t):
    return Frame(index=int(t * 10), timestamp=t, image=np.zeros((4, 4, 3), np.uint8))


def test_prompt_includes_tracker_facts_and_history():
    prompt = build_prompt(
        [Event("entered", 3, "person", 1.2)], Counter(person=2, ball=1), ["What a start!"]
    )
    assert "2 person, 1 ball" in prompt
    assert "person #3 entered at 1.2s" in prompt
    assert "What a start!" in prompt


def test_prompt_with_sport_names_it_and_drops_detector_labels():
    prompt = build_prompt(
        [Event("entered", 3, "frisbee", 1.2)],
        Counter(person=2, frisbee=1),
        ["What a start!"],
        sport="cricket",
    )
    assert "live cricket commentator" in prompt
    assert "frisbee" not in prompt
    assert "Detected on screen" not in prompt
    assert "What a start!" in prompt


def test_clean_sport_makes_one_short_line():
    assert clean_sport("  cricket\n") == "cricket"
    assert clean_sport("ice\n\nhockey") == "ice hockey"
    assert clean_sport(None) == ""
    assert len(clean_sport("x" * 500)) == 40


def test_clean_line_keeps_first_line_without_quotes():
    assert clean_line(' "He shoots!"\nextra') == "He shoots!"
    assert clean_line("   ") == ""
    assert clean_line("Goal! What a strike. Unbelievable") == "Goal!"


def test_feed_requests_lines_on_interval_with_events():
    calls, lines = [], []
    done = threading.Event()

    def fake_vlm(images, prompt):
        calls.append((len(images), prompt))
        return f"line {len(calls)}"

    def on_line(line):
        lines.append(line)
        done.set()

    feed = CommentaryFeed(fake_vlm, on_line, interval=1.0, frames_per_line=2)
    feed.push(frame(0.0), [Event("entered", 1, "person", 0.0)], Counter(person=1))
    feed.push(frame(0.5), [], Counter(person=1))
    assert calls == []  # not due yet
    feed.push(frame(1.0), [], Counter(person=1))
    assert done.wait(2)
    feed.close()

    assert len(calls) == 1
    n_images, prompt = calls[0]
    assert n_images == 2
    assert "person #1 entered" in prompt
    assert lines[0].text == "line 1" and lines[0].timestamp == 1.0


def test_feed_skips_while_busy_and_keeps_events():
    release, finished = threading.Event(), threading.Event()
    prompts = []

    def slow_vlm(images, prompt):
        prompts.append(prompt)
        release.wait(2)
        return "ok"

    feed = CommentaryFeed(slow_vlm, lambda line: finished.set(), interval=1.0)
    feed.push(frame(0.0), [], Counter())  # starts the clock
    feed.push(frame(1.0), [], Counter())  # first request
    feed.push(frame(2.0), [Event("left", 9, "ball", 2.0)], Counter())  # busy: skipped
    assert len(prompts) <= 1
    release.set()
    assert finished.wait(2)
    for _ in range(100):  # worker clears busy right after on_line
        if not feed._busy.is_set():
            break
        time.sleep(0.01)
    feed.push(frame(2.5), [], Counter())
    feed.close()

    assert len(prompts) == 2
    assert "ball #9 left" in prompts[1]  # event carried over to the next line
