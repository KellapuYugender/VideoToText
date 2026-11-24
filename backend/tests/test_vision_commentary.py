import threading
import time

import numpy as np

from vision.commentary import CommentaryFeed, build_prompt, clean_line, clean_sport
from vision.source import Frame


def frame(t):
    return Frame(index=int(t * 10), timestamp=t, image=np.zeros((4, 4, 3), np.uint8))


def test_prompt_without_sport_narrates_neutrally():
    prompt = build_prompt(["A man crosses the road."])
    assert "live narrator" in prompt
    assert "sport" not in prompt and "commentator" not in prompt
    assert "A man crosses the road." in prompt


def test_prompt_with_sport_commentates_it():
    prompt = build_prompt(["What a start!"], sport="cricket")
    assert "live cricket commentator" in prompt
    assert "What a start!" in prompt
    assert "next line of commentary" in prompt


def test_first_prompt_asks_for_an_opening_line_about_what_is_visible():
    prompt = build_prompt([], sport="cricket")
    assert "opening line of commentary" in prompt
    assert "what you can see" in prompt
    assert "previous lines" not in prompt


def test_clean_sport_makes_one_short_line():
    assert clean_sport("  cricket\n") == "cricket"
    assert clean_sport("ice\n\nhockey") == "ice hockey"
    assert clean_sport(None) == ""
    assert len(clean_sport("x" * 500)) == 40


def test_clean_line_keeps_first_line_without_quotes():
    assert clean_line(' "He shoots!"\nextra') == "He shoots!"
    assert clean_line("   ") == ""
    assert clean_line("Goal! What a strike. Unbelievable") == "Goal!"


def test_clean_line_unwraps_quoted_fragments_and_capitalises():
    assert clean_line("'the city's busy'.") == "The city's busy."
    assert clean_line("“Six”") == "Six"
    assert clean_line("a man walks by.") == "A man walks by."


def test_feed_requests_lines_on_interval():
    calls, lines = [], []
    done = threading.Event()

    def fake_vlm(images, prompt):
        calls.append((len(images), prompt))
        return f"line {len(calls)}"

    def on_line(line):
        lines.append(line)
        done.set()

    feed = CommentaryFeed(fake_vlm, on_line, interval=1.0, frames_per_line=2)
    feed.push(frame(0.0))
    feed.push(frame(0.5))
    assert calls == []  # not due yet
    feed.push(frame(1.0))
    assert done.wait(2)
    feed.close()

    assert len(calls) == 1
    n_images, prompt = calls[0]
    assert n_images == 2
    assert "live narrator" in prompt
    assert lines[0].text == "line 1" and lines[0].timestamp == 1.0


def test_feed_skips_while_busy_and_remembers_previous_lines():
    release, finished = threading.Event(), threading.Event()
    prompts = []

    def slow_vlm(images, prompt):
        prompts.append(prompt)
        release.wait(2)
        return "ok"

    feed = CommentaryFeed(slow_vlm, lambda line: finished.set(), interval=1.0)
    feed.push(frame(0.0))  # starts the clock
    feed.push(frame(1.0))  # first request
    feed.push(frame(2.0))  # busy: skipped
    assert len(prompts) <= 1
    release.set()
    assert finished.wait(2)
    for _ in range(100):  # worker clears busy right after on_line
        if not feed._busy.is_set():
            break
        time.sleep(0.01)
    feed.push(frame(2.5))
    feed.close()

    assert len(prompts) == 2
    assert "ok" in prompts[1]  # the first line is passed on so it isn't repeated
