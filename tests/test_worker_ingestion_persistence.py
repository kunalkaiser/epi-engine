from pathlib import Path

from apps.worker.ingestion import InMemoryStagingStore, ingest_file


class FakeRunStore:
    def __init__(self) -> None:
        self.started = False
        self.completed = False
        self.failed = False
        self.run_id = "ing_test"

    def start_run(self, **_: object) -> str:
        self.started = True
        return self.run_id

    def complete_run(self, **_: object) -> None:
        self.completed = True

    def fail_run(self, **_: object) -> None:
        self.failed = True


def test_ingestion_run_store_is_called_for_success(tmp_path: Path) -> None:
    csv_path = tmp_path / "patient_summary.csv"
    csv_path.write_text(
        "\n".join(
            [
                "population_label,age_band,sex,count",
                "Adults with type 2 diabetes,45-64,female,18240",
            ]
        ),
        encoding="utf-8",
    )
    run_store = FakeRunStore()
    ingest_file(
        dataset="patient_summary",
        input_path=csv_path,
        source_kind="synthetic",
        staging_store=InMemoryStagingStore(),
        run_store=run_store,
        tenant_id="tenant-a",
    )
    assert run_store.started is True
    assert run_store.completed is True
    assert run_store.failed is False
