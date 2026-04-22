import json

import pytest

from apps.worker.clustering import run_clustering_pipeline


def test_kmeans_pipeline_returns_deterministic_cluster_summaries(tmp_path) -> None:
    input_path = tmp_path / "synthetic_clusters.csv"
    input_path.write_text(
        "\n".join(
            [
                "cohort_id,incidence_rate,prevalence_rate,unmet_need_index,market_size_index,equity_index",
                "c1,10,12,15,18,20",
                "c2,11,13,14,19,21",
                "c3,78,82,70,68,55",
                "c4,80,79,72,69,57",
                "c5,42,39,50,47,75",
                "c6,44,41,52,49,74",
            ]
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "kmeans-report.json"

    report = run_clustering_pipeline(
        input_path=input_path,
        output_path=output_path,
        source_kind="synthetic",
        feature_columns=[
            "incidence_rate",
            "prevalence_rate",
            "unmet_need_index",
            "market_size_index",
            "equity_index",
        ],
        algorithm="kmeans",
        n_clusters=3,
        random_seed=42,
    )

    assert report.metrics.algorithm == "kmeans"
    assert report.metrics.cluster_count == 3
    assert report.metrics.noise_count == 0
    assert report.metrics.inertia is not None
    assert report.metrics.silhouette_score is not None
    assert [summary.cohort_count for summary in report.cluster_summaries] == [2, 2, 2]

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["metrics"]["cluster_count"] == 3
    assert len(written["cluster_summaries"]) == 3


def test_dbscan_pipeline_reports_noise_and_clusters(tmp_path) -> None:
    input_path = tmp_path / "deidentified_clusters.csv"
    input_path.write_text(
        "\n".join(
            [
                "cohort_id,incidence_rate,prevalence_rate,unmet_need_index,market_size_index,equity_index",
                "c1,10,10,10,10,10",
                "c2,11,10,9,10,10",
                "c3,50,51,48,49,47",
                "c4,51,52,49,50,48",
                "c5,95,5,95,5,95",
            ]
        ),
        encoding="utf-8",
    )

    report = run_clustering_pipeline(
        input_path=input_path,
        source_kind="deidentified",
        feature_columns=[
            "incidence_rate",
            "prevalence_rate",
            "unmet_need_index",
            "market_size_index",
            "equity_index",
        ],
        algorithm="dbscan",
        eps=0.6,
        min_samples=2,
    )

    assert report.metrics.algorithm == "dbscan"
    assert report.metrics.cluster_count == 2
    assert report.metrics.noise_count == 1
    assert report.metrics.inertia is None
    assert any(summary.cluster_id == -1 for summary in report.cluster_summaries)


def test_pipeline_rejects_non_aggregate_source_kind(tmp_path) -> None:
    input_path = tmp_path / "clusters.csv"
    input_path.write_text(
        "\n".join(
            [
                "cohort_id,incidence_rate",
                "c1,10",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="synthetic or deidentified"):
        run_clustering_pipeline(
            input_path=input_path,
            source_kind="production",  # type: ignore[arg-type]
            feature_columns=["incidence_rate"],
        )


def test_pipeline_rejects_identifiable_columns(tmp_path) -> None:
    input_path = tmp_path / "clusters.csv"
    input_path.write_text(
        "\n".join(
            [
                "mrn,incidence_rate",
                "123,10",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden identifiable columns"):
        run_clustering_pipeline(
            input_path=input_path,
            source_kind="synthetic",
            feature_columns=["incidence_rate"],
        )


def test_pipeline_rejects_missing_input_file(tmp_path) -> None:
    missing_path = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError, match="input file does not exist"):
        run_clustering_pipeline(
            input_path=missing_path,
            source_kind="synthetic",
            feature_columns=["incidence_rate"],
        )
