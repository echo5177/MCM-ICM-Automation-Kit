from __future__ import annotations

import hashlib
from pathlib import Path

from mcm_workflow_kit.config import WorkflowConfig
from mcm_workflow_kit.source_checker import REQUIRED_COLUMNS, discussion_host, run_source_checks


def test_discussion_host_matches_the_platform_and_its_subdomains():
    assert discussion_host("https://blog.csdn.net/user/article/details/1") == "csdn.net"
    assert discussion_host("https://www.zhihu.com/question/1") == "zhihu.com"
    assert discussion_host("https://mp.weixin.qq.com/s/abc") == "mp.weixin.qq.com"
    assert discussion_host("https://web.calce.umd.edu/batteries/data/x.zip") == ""
    assert discussion_host("https://notcsdn.net/x") == ""  # a suffix match needs a dot
    assert discussion_host("https://forum.example.org/t/1", ("example.org",)) == "example.org"


def write_manifest(tmp_path: Path, url: str) -> WorkflowConfig:
    data = tmp_path / "data" / "raw" / "external"
    data.mkdir(parents=True)
    payload = b"hour,load\n0,1.2\n"
    (data / "load.csv").write_bytes(payload)
    row = {column: "x" for column in REQUIRED_COLUMNS}
    row.update(source_id="load_profile", dataset_name="Hourly load", source_type="external",
               url=url, access_date="2027-01-29", local_path="data/raw/external/load.csv",
               sha256=hashlib.sha256(payload).hexdigest())
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "data_source_manifest.csv").write_text(
        ",".join(REQUIRED_COLUMNS) + "\n" + ",".join(row[c] for c in REQUIRED_COLUMNS) + "\n", encoding="utf-8")
    return WorkflowConfig.from_mapping({"data_source_manifest": "reports/data_source_manifest.csv"})


def test_source_from_a_contest_discussion_platform_fails(tmp_path):
    config = write_manifest(tmp_path, "https://blog.csdn.net/someone/article/details/123456")
    result = run_source_checks(tmp_path, config)
    failed = " ".join(m.message for m in result.messages if m.level == "fail")
    assert "load_profile comes from csdn.net" in failed and "primary source" in failed


def test_source_from_its_publisher_is_not_flagged(tmp_path):
    config = write_manifest(tmp_path, "https://data.example.gov/load/hourly.csv")
    assert not any("discussed" in m.message for m in run_source_checks(tmp_path, config).messages)
