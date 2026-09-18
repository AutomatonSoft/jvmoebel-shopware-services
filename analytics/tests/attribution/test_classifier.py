from domains.attribution.classifier import classify_source

EMPTY = {
    "gclid": None,
    "gbraid": None,
    "wbraid": None,
    "utm_source": None,
    "utm_medium": None,
    "referrer": None,
}


def test_click_id_is_google_ads() -> None:
    assert (
        classify_source(
            **{
                **EMPTY,
                "gclid": "Cj0KCQjw-example",
                "utm_source": "google",
                "utm_medium": "cpc",
                "referrer": "https://www.google.com/",
            }
        )
        == "google_ads"
    )


def test_google_cpc_without_click_id_is_google_ads() -> None:
    assert (
        classify_source(**{**EMPTY, "utm_source": "google", "utm_medium": "cpc"})
        == "google_ads"
    )


def test_organic_medium_is_seo() -> None:
    assert (
        classify_source(**{**EMPTY, "utm_source": "google", "utm_medium": "organic"})
        == "seo"
    )


def test_search_referrer_without_utm_is_seo() -> None:
    assert classify_source(**{**EMPTY, "referrer": "https://www.google.com/"}) == "seo"
    assert (
        classify_source(**{**EMPTY, "referrer": "https://www.bing.com/search"}) == "seo"
    )


def test_mail_google_referrer_is_not_seo() -> None:
    assert (
        classify_source(**{**EMPTY, "referrer": "https://mail.google.com/"})
        == "referral"
    )


def test_social_source() -> None:
    assert (
        classify_source(**{**EMPTY, "utm_source": "instagram", "utm_medium": "social"})
        == "social"
    )


def test_referrer_without_utm_is_referral() -> None:
    assert (
        classify_source(**{**EMPTY, "referrer": "https://example.com/blog"})
        == "referral"
    )


def test_utm_medium_referral_is_referral() -> None:
    assert (
        classify_source(
            **{
                **EMPTY,
                "utm_source": "affiliate",
                "utm_medium": "referral",
            }
        )
        == "referral"
    )


def test_email_medium_is_email() -> None:
    assert (
        classify_source(**{**EMPTY, "utm_source": "newsletter", "utm_medium": "email"})
        == "email"
    )


def test_bing_cpc_is_paid() -> None:
    assert (
        classify_source(**{**EMPTY, "utm_source": "bing", "utm_medium": "cpc"})
        == "paid"
    )


def test_empty_is_direct() -> None:
    assert classify_source(**EMPTY) == "direct"


def test_unknown_utm_is_other() -> None:
    assert (
        classify_source(**{**EMPTY, "utm_source": "youtube", "utm_medium": "video"})
        == "social"
    )
    assert (
        classify_source(**{**EMPTY, "utm_source": "partner", "utm_medium": "video"})
        == "other"
    )
