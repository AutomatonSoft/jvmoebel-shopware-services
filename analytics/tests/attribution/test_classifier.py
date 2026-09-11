from domains.attribution.classifier import classify_source


def test_click_id_is_google_ads() -> None:
    assert (
        classify_source(
            gclid="Cj0KCQjw-example",
            gbraid=None,
            wbraid=None,
            utm_source="google",
            utm_medium="cpc",
            referrer="https://www.google.com/",
        )
        == "google_ads"
    )


def test_organic_medium_is_seo() -> None:
    assert (
        classify_source(
            gclid=None,
            gbraid=None,
            wbraid=None,
            utm_source="google",
            utm_medium="organic",
            referrer=None,
        )
        == "seo"
    )


def test_social_source() -> None:
    assert (
        classify_source(
            gclid=None,
            gbraid=None,
            wbraid=None,
            utm_source="instagram",
            utm_medium="social",
            referrer=None,
        )
        == "social"
    )


def test_referrer_without_utm_is_referral() -> None:
    assert (
        classify_source(
            gclid=None,
            gbraid=None,
            wbraid=None,
            utm_source=None,
            utm_medium=None,
            referrer="https://example.com/blog",
        )
        == "referral"
    )


def test_empty_is_direct() -> None:
    assert (
        classify_source(
            gclid=None,
            gbraid=None,
            wbraid=None,
            utm_source=None,
            utm_medium=None,
            referrer=None,
        )
        == "direct"
    )


def test_other_utm_is_other() -> None:
    assert (
        classify_source(
            gclid=None,
            gbraid=None,
            wbraid=None,
            utm_source="newsletter",
            utm_medium="email",
            referrer=None,
        )
        == "other"
    )
