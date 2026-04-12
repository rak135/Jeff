from jeff.cognitive.research import web as web_module


def test_obvious_html_tags_are_stripped() -> None:
    html = "<html><body><article><p>Bounded rollout stays narrow.</p></article></body></html>"

    cleaned = web_module._clean_html_excerpt(html, max_chars=200)

    assert cleaned == "Bounded rollout stays narrow."


def test_obvious_js_and_css_boilerplate_is_reduced() -> None:
    html = (
        "<style>body{color:red;} .hero{display:none;}</style>"
        "<script>window.track=function(){return false;}</script>"
        "<div>Useful support text survives.</div>"
    )

    cleaned = web_module._clean_html_excerpt(html, max_chars=200)

    assert "body{color:red;}" not in cleaned
    assert "window.track" not in cleaned
    assert "Useful support text survives." in cleaned


def test_whitespace_normalization_works() -> None:
    cleaned = web_module._clean_web_excerpt_text(" Useful \n\n  support\ttext  here ", max_chars=200)

    assert cleaned == "Useful support text here"


def test_cleaned_snippets_remain_bounded() -> None:
    raw = "Bounded support text. " * 50

    cleaned = web_module._clean_web_excerpt_text(raw, max_chars=60)

    assert len(cleaned) == 60


def test_useful_text_is_preserved_when_present() -> None:
    html = "<div><p>The bounded rollout remains stable and avoids widening scope.</p></div>"

    cleaned = web_module._clean_html_excerpt(html, max_chars=200)

    assert "bounded rollout remains stable" in cleaned.lower()


def test_over_cleaning_does_not_collapse_reasonable_input_into_nothing() -> None:
    html = (
        "<style>body{margin:0;}</style>"
        "<div>Useful support survives.</div>"
        "<script>const x = 1;</script>"
    )

    cleaned = web_module._clean_html_excerpt(html, max_chars=200)

    assert cleaned == "Useful support survives."
