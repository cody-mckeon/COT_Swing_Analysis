import io
import json
import os
import zipfile
import importlib.util
from pathlib import Path

import pytest


def test_weekly_etl(tmp_path, monkeypatch):

    # create dummy zip files: historical 2006-2016 and individual 2017
    hist_zip = io.BytesIO()
    with zipfile.ZipFile(hist_zip, "w") as zf:
        zf.writestr("fut_disagg_2016.xls", b"hist")
        zf.writestr("fut_disagg_2008.xls", b"hist")
    hist_zip.seek(0)

    year_zip = io.BytesIO()
    with zipfile.ZipFile(year_zip, "w") as zf:
        zf.writestr("fut_disagg_2017.xls", b"year")
    year_zip.seek(0)

    # create a dummy zip containing one Excel file
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.xls", b"dummy")
    buf.seek(0)

    class DummyResp:
        def __init__(self, data):
            self.content = data

        def raise_for_status(self):
            pass

    def dummy_get(url):

        if "hist_2006_2016" in url:
            return DummyResp(hist_zip.getvalue())
        return DummyResp(year_zip.getvalue())

    monkeypatch.setattr("requests.get", dummy_get)

    calls = []

    def dummy_call(cmd, *a, **k):
        calls.append(cmd)

    # load the script as a module so we can patch its functions
    spec = importlib.util.spec_from_file_location("weekly_etl", "scripts/weekly_etl.py")
    etl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(etl)

    monkeypatch.setattr(etl, "requests", pytest.importorskip("requests"))
    monkeypatch.setattr(etl.requests, "get", dummy_get)
    monkeypatch.setattr(etl.subprocess, "check_call", dummy_call)
    monkeypatch.setattr(
        etl.service_account.Credentials,
        "from_service_account_info",
        lambda info: object(),
    )
    monkeypatch.setattr(etl, "build", lambda *a, **kw: object())

    class FakeDatetime:
        @classmethod
        def now(cls):
            class D:  # noqa: D401

                year = 2008

            return D()

    monkeypatch.setattr(etl, "datetime", FakeDatetime)

    env = {
        "GDRIVE_SA_KEY": json.dumps({"dummy": True}),
        "RAW_DATA_FOLDER_ID": "1",
        "RAW_DATA_DIR": str(tmp_path),
        "PROCESSED_DIR": str(tmp_path / "processed"),
    }
    monkeypatch.setenv("GDRIVE_SA_KEY", env["GDRIVE_SA_KEY"])
    monkeypatch.setenv("RAW_DATA_FOLDER_ID", env["RAW_DATA_FOLDER_ID"])
    monkeypatch.setenv("RAW_DATA_DIR", env["RAW_DATA_DIR"])
    monkeypatch.setenv("PROCESSED_DIR", env["PROCESSED_DIR"])

    exit_code = etl.main()
    assert exit_code == 0

    assert (tmp_path / "cot_2016.xls").exists()
    assert (tmp_path / "cot_2017.xls").exists()

    assert (tmp_path / "cot_2008.xls").exists()

    assert any(
        "make_dataset.py" in str(c[1]) if isinstance(c, list) else False for c in calls
    )


def test_weekly_etl_upload(tmp_path, monkeypatch):
    hist_zip = io.BytesIO()
    with zipfile.ZipFile(hist_zip, "w") as zf:
        zf.writestr("fut_disagg_2016.xls", b"hist")
    hist_zip.seek(0)

    def dummy_get(url):
        return type(
            "Resp",
            (),
            {"content": hist_zip.getvalue(), "raise_for_status": lambda self: None},
        )()

    spec = importlib.util.spec_from_file_location("weekly_etl", "scripts/weekly_etl.py")
    etl = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(etl)

    monkeypatch.setattr(etl.requests, "get", dummy_get)

    def dummy_call(cmd, *a, **k):
        processed = Path(os.environ["PROCESSED_DIR"])
        processed.mkdir(parents=True, exist_ok=True)
        (processed / "cot_gold.csv").write_text("x")

    monkeypatch.setattr(etl.subprocess, "check_call", dummy_call)
    monkeypatch.setattr(
        etl.service_account.Credentials,
        "from_service_account_info",
        lambda info: object(),
    )
    monkeypatch.setattr(
        etl,
        "build",
        lambda *a, **kw: type(
            "Drive",
            (),
            {
                "files": lambda self: type(
                    "F",
                    (),
                    {"create": lambda **k: type("R", (), {"execute": lambda: None})()},
                )()
            },
        )(),
    )

    uploaded = []
    monkeypatch.setattr(etl, "upload_file", lambda *a: uploaded.append(a))

    monkeypatch.setenv("GDRIVE_SA_KEY", json.dumps({"dummy": True}))
    monkeypatch.setenv("RAW_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("RAW_DATA_FOLDER_ID", "1")
    monkeypatch.setenv("PROCESSED_DIR", str(tmp_path / "processed"))
    monkeypatch.setenv("PROCESSED_FOLDER_ID", "2")

    exit_code = etl.main()
    assert exit_code == 0
    assert uploaded
