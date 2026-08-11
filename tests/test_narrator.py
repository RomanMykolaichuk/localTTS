from localtts.narrator import prepare_without_llm


def test_fallback_plan_has_pauses_and_final_zero():
    plan = prepare_without_llm("Перше речення. Друге речення.\n\nНовий абзац.")
    assert len(plan.segments) == 3
    assert plan.segments[0].pause_after_ms == 320
    assert plan.segments[1].pause_after_ms == 600
    assert plan.segments[-1].pause_after_ms == 0
    assert plan.segments[0].tts_text == "Перше речення."
