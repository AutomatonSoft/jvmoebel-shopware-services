from typing import TypedDict

from domains.attribution.classifier import (
    classify_source,
    collect_referral_exclusion_hosts,
)


class _ClassifyKwargs(TypedDict):
    gclid: str | None
    gbraid: str | None
    wbraid: str | None
    utm_source: str | None
    utm_medium: str | None
    referrer: str | None


EMPTY: _ClassifyKwargs = {
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


def test_social_referrer_without_utm_is_social() -> None:
    for referrer in (
        "https://www.instagram.com/",
        "https://l.instagram.com/",
        "https://www.facebook.com/",
        "https://l.facebook.com/",
        "https://www.tiktok.com/@shop",
        "https://www.pinterest.com/pin/1",
        "https://www.pinterest.de/pin/1",
        "https://t.co/abc",
        "https://lnkd.in/abc",
        "https://pin.it/abc",
    ):
        assert classify_source(**{**EMPTY, "referrer": referrer}) == "social"


def test_utm_wins_over_social_referrer() -> None:
    assert (
        classify_source(
            **{
                **EMPTY,
                "utm_source": "bing",
                "utm_medium": "cpc",
                "referrer": "https://l.facebook.com/",
            }
        )
        == "paid"
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


def test_payment_referrer_is_direct_when_excluded() -> None:
    excluded = collect_referral_exclusion_hosts()
    for referrer in (
        "https://www.paypal.com/checkoutnow",
        "https://checkout.paypal.de/",
        "https://pay.klarna.com/eu",
        "https://checkout.stripe.com/c/pay/cs_test",
        "https://secure.3dsecure.visa.com/auth",
        "https://acs.sparkasse.de/tdsecure",
        "https://www.sofort.com/payment",
        "https://secure.payone.de/3ds",
    ):
        assert (
            classify_source(
                **{**EMPTY, "referrer": referrer},
                excluded_hosts=excluded,
            )
            == "direct"
        )


def test_acs_com_is_not_excluded() -> None:
    excluded = collect_referral_exclusion_hosts()
    assert (
        classify_source(
            **{**EMPTY, "referrer": "https://acs.com/"},
            excluded_hosts=excluded,
        )
        == "referral"
    )


def test_own_shop_origin_is_direct() -> None:
    excluded = collect_referral_exclusion_hosts(
        origin_urls=["https://www.jvmoebel.de"],
    )
    assert (
        classify_source(
            **{**EMPTY, "referrer": "https://www.jvmoebel.de/checkout"},
            excluded_hosts=excluded,
        )
        == "direct"
    )
    assert (
        classify_source(
            **{**EMPTY, "referrer": "https://checkout.jvmoebel.de/return"},
            excluded_hosts=excluded,
        )
        == "direct"
    )


def test_extra_exclusion_host() -> None:
    excluded = collect_referral_exclusion_hosts(extra=["bank-acs.example"])
    assert (
        classify_source(
            **{**EMPTY, "referrer": "https://bank-acs.example/3ds"},
            excluded_hosts=excluded,
        )
        == "direct"
    )


def test_click_id_wins_over_excluded_referrer() -> None:
    excluded = collect_referral_exclusion_hosts()
    assert (
        classify_source(
            **{
                **EMPTY,
                "gclid": "Cj0KCQjw-example",
                "referrer": "https://www.paypal.com/",
            },
            excluded_hosts=excluded,
        )
        == "google_ads"
    )


def test_excluded_referrer_does_not_drop_explicit_utm() -> None:
    excluded = collect_referral_exclusion_hosts()
    assert (
        classify_source(
            **{
                **EMPTY,
                "utm_source": "partner",
                "utm_medium": "referral",
                "referrer": "https://www.paypal.com/",
            },
            excluded_hosts=excluded,
        )
        == "referral"
    )
