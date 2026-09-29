"""Regression vectors for the web signer.

Captured from a live douyin page: the query secsdk was handed, the ``uifid``
it was bound to, the timestamp it chose, and the signature it emitted. They
must reproduce byte for byte.
"""

from sign.websign import SALT, canonical_query, is_protected, websign_sign

REAL_UIFID = "1eef1c80f1a85c3b9f707a45d635c2febe06ee5786dbc4c5c1db20e6dd0040a22fe57ae215d03a89e898e1bed82e737395591e9b0e9c18a33e6463cbb802eb00fbbcb07abaefb9532af73ba693e9e30da33d6a43c893dc8cd31447414d093f0b2beb04ac9f9e6a8f258f62e59cac5e8207a8c7c2bbd8285624956ae105986c7bc24e07f31938979ee7a7832b00819b179bc1794020afdc37fda7a70a8502ea4d"
REAL_QUERY = (
    "device_platform=webapp&"
    "aid=6383&"
    "channel=channel_pc_web&"
    "aweme_id=719004219116988&"
    "pc_client_type=1&"
    "version_code=190500&"
    "version_name=19.5.0&"
    "cookie_enabled=true&"
    "screen_width=1536&"
    "screen_height=864&"
    "browser_language=en-US&"
    "browser_platform=Linux%20x86_64&"
    "browser_name=Chrome&"
    "browser_version=154.0.0.0&"
    "browser_online=true&"
    "engine_name=Blink&"
    "engine_version=154.0.0.0&"
    "os_name=Linux&"
    "os_version=x86_64&"
    "cpu_core_num=2&"
    "device_memory=2&"
    "platform=PC&"
    "downlink=1.6&"
    "effective_type=4g&"
    "round_trip_time=100&"
    "a_bogus=QXDdhfw2kv2TXj6v5IoLfY3q6fp3YdBr0trEMD2fydvTkL39HMOd9exoAzzvrEujFs%2FjIeYjy4hbT3ohrQ2y8qwf9W0L%2F25gsDSkKl12so0j53inCLf%2FE0iE5hsAtFH8svr4iKi8owICSYyhldAJ5kIlO62-zo0%2F9lYD&"
    "uifid=1eef1c80f1a85c3b9f707a45d635c2febe06ee5786dbc4c5c1db20e6dd0040a22fe57ae215d03a89e898e1bed82e737395591e9b0e9c18a33e6463cbb802eb00fbbcb07abaefb9532af73ba693e9e30da33d6a43c893dc8cd31447414d093f0b2beb04ac9f9e6a8f258f62e59cac5e8207a8c7c2bbd8285624956ae105986c7bc24e07f31938979ee7a7832b00819b179bc1794020afdc37fda7a70a8502ea4d"
)
REAL_TIMESTAMP = 1790691091
REAL_SIGNATURE = "be7d5fcbf405104a7d1b49e039c8486c"


def test_real_browser_vector():
    """Our signature must equal the one the browser emitted for the same inputs."""
    signed, sig = websign_sign(REAL_QUERY, REAL_UIFID, timestamp=REAL_TIMESTAMP)
    assert sig == REAL_SIGNATURE
    assert signed.endswith("&x-secsdk-web-signature=" + REAL_SIGNATURE)
    assert signed.startswith(REAL_QUERY)


def test_canonical_query_is_the_sent_bytes():
    """The preimage is the query as sent: re-canonicalising it is a no-op."""
    once = canonical_query(REAL_QUERY)
    assert canonical_query(once) == once


def test_canonical_query_escapes_like_urlsearchparams():
    assert canonical_query("a=hello world&b=x+y&c=100%&d=%7E") == (
        "a=hello%20world&b=x%2By&c=100%25&d=~"
    )
    assert canonical_query("k=/slash") == "k=%2Fslash"


def test_uifid_appended_only_when_absent():
    with_id, _ = websign_sign("a=1&uifid=deadbeef", "other", timestamp=1)
    assert with_id.count("uifid=") == 1
    without, _ = websign_sign("a=1", "deadbeef", timestamp=1)
    assert without.startswith("a=1&uifid=deadbeef&timestamp=1&x-secsdk-web-signature=")


def test_protected_paths():
    assert is_protected("/aweme/v1/web/aweme/detail/")
    assert is_protected("/aweme/v1/web/tab/feed/", "POST")
    assert not is_protected("/aweme/v1/web/hot/search/list/")
    assert SALT == "A96D855A08C0A9707F8BEF0D9A527E4E"
