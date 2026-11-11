import hashlib
import sqlite3
import zlib

import pytest

import listing_coverage_epfl as C


def fixture():
    con = sqlite3.connect(":memory:")
    con.execute("create table plan(year integer,half text,page_url text,capture_url text,wayback_timestamp text,status text,reason text,slot text)")
    con.execute("create table captures(capture_url text,http_status integer,sha256 text,raw_zlib blob,final_url text)")
    source = "www.epfl.ch/schools/ic/about/faculty-members/"
    cap = "https://web.archive.org/web/20200926102906id_/https://" + source
    body = '<div class="contact-list-row"><a itemprop="name">Person %s</a><p itemprop="jobTitle">Professor</p></div>'
    raw = "".join(body % i for i in range(5)).encode()
    con.execute("insert into plan values(?,?,?,?,?,?,?,?)", (2020, "H2", source, cap, "20200926102906", "ok", None, C.SLOT))
    con.execute("insert into captures values(?,?,?,?,?)", (cap, 200, hashlib.sha256(raw).hexdigest(), zlib.compress(raw), cap))
    return con, [(source, "20190101", "20261231")]


def test_real_capture_proves_one_department_year():
    con, sources = fixture()
    coverage, receipts = C.coverage_from_captures(con, sources, range(2020, 2021))
    assert coverage == {"2020": {C.SLOT + " H2": "ok"}}
    assert receipts[0]["people"] == 5
    assert receipts[0]["sha256"]


def test_missing_year_or_corrupt_bytes_never_passes():
    con, sources = fixture()
    with pytest.raises(ValueError, match="2021"):
        C.coverage_from_captures(con, sources, range(2020, 2022))
    con.execute("update captures set sha256=?", ("0" * 64,))
    with pytest.raises(ValueError, match="hash mismatch"):
        C.coverage_from_captures(con, sources, range(2020, 2021))
