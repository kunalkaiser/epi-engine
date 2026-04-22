from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd

from apps.api.logging_utils import get_logger, log_event


SourceKind = Literal["synthetic", "deidentified"]
Algorithm = Literal["kmeans", "dbscan"]

FORBIDDEN_COLUMNS = {
    "first_name",
    "last_name",
    "full_name",
    "address",
    "phone",
    "email",
    "ssn",
    "mrn",
}

logger = get_logger("epi_engine.worker.clustering")


@dataclass(frozen=True)
class ClusterSummary:
    cluster_id: int
    cohort_count: int
    share_of_rows: float
    feature_means: dict[str, float]
    feature_mins: dict[str, float]
    feature_maxs: dict[str, float]


@dataclass(frozen=True)
class EvaluationMetrics:
    algorithm: str
    row_count: int
    cluster_count: int
    noise_count: int
    silhouette_score: float | None
    davies_bouldin_score: float | None
    inertia: float | None


@dataclass(frozen=True)
class ClusteringReport:
    source_kind: SourceKind
    algorithm: Algorithm
    feature_columns: list[str]
    metrics: EvaluationMetrics
    cluster_summaries: list[ClusterSummary]


def run_clustering_pipeline(
    input_path: str | Path,
    source_kind: SourceKind,
    feature_columns: list[str],
    algorithm: Algorithm = "kmeans",
    output_path: str | Path | None = None,
    n_clusters: int = 3,
    random_seed: int = 42,
    max_iter: int = 100,
    eps: float = 0.8,
    min_samples: int = 2,
) -> ClusteringReport:
    _validate_source_kind(source_kind)
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"input file does not exist: {input_path}")

    log_event(logger, logging.INFO, "clustering.started", algorithm=algorithm, input_path=str(input_path))
    frame = _load_frame(input_path)
    _validate_columns(frame, feature_columns)
    scaled_points = _standardize(frame[feature_columns].to_numpy(dtype=float))

    if algorithm == "kmeans":
        labels, inertia = run_kmeans(
            scaled_points,
            n_clusters=n_clusters,
            random_seed=random_seed,
            max_iter=max_iter,
        )
    elif algorithm == "dbscan":
        labels = run_dbscan(
            scaled_points,
            eps=eps,
            min_samples=min_samples,
        )
        inertia = None
    else:
        raise ValueError(f"unsupported algorithm: {algorithm}")

    metrics = evaluate_clustering(
        scaled_points,
        labels,
        algorithm=algorithm,
        inertia=inertia,
    )
    summaries = summarize_clusters(frame, labels, feature_columns)
    report = ClusteringReport(
        source_kind=source_kind,
        algorithm=algorithm,
        feature_columns=feature_columns,
        metrics=metrics,
        cluster_summaries=summaries,
    )

    if output_path is not None:
        Path(output_path).write_text(json.dumps(asdict(report), indent=2), encoding="utf-8")

    log_event(
        logger,
        logging.INFO,
        "clustering.completed",
        algorithm=algorithm,
        cluster_count=report.metrics.cluster_count,
        noise_count=report.metrics.noise_count,
    )
    return report


def run_kmeans(
    points: np.ndarray,
    n_clusters: int,
    random_seed: int = 42,
    max_iter: int = 100,
) -> tuple[np.ndarray, float]:
    if n_clusters < 1:
        raise ValueError("n_clusters must be at least 1")
    if points.shape[0] < n_clusters:
        raise ValueError("n_clusters cannot exceed the number of rows")

    rng = np.random.default_rng(random_seed)
    initial_indices = rng.choice(points.shape[0], size=n_clusters, replace=False)
    centroids = points[initial_indices].copy()

    for _ in range(max_iter):
        distances = _pairwise_distances(points, centroids)
        labels = np.argmin(distances, axis=1)
        new_centroids = centroids.copy()

        for cluster_id in range(n_clusters):
            members = points[labels == cluster_id]
            if members.size == 0:
                replacement_index = int(rng.integers(0, points.shape[0]))
                new_centroids[cluster_id] = points[replacement_index]
            else:
                new_centroids[cluster_id] = members.mean(axis=0)

        if np.allclose(new_centroids, centroids):
            centroids = new_centroids
            break
        centroids = new_centroids

    final_distances = _pairwise_distances(points, centroids)
    final_labels = np.argmin(final_distances, axis=1)
    inertia = float(np.sum((points - centroids[final_labels]) ** 2))
    return final_labels.astype(int), round(inertia, 6)


def run_dbscan(points: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    if eps <= 0:
        raise ValueError("eps must be greater than zero")
    if min_samples < 1:
        raise ValueError("min_samples must be at least 1")

    labels = np.full(points.shape[0], -1, dtype=int)
    visited = np.zeros(points.shape[0], dtype=bool)
    cluster_id = 0

    for index in range(points.shape[0]):
        if visited[index]:
            continue

        visited[index] = True
        neighbors = _region_query(points, index, eps)
        if len(neighbors) < min_samples:
            labels[index] = -1
            continue

        labels[index] = cluster_id
        seeds = list(neighbors)
        pointer = 0

        while pointer < len(seeds):
            neighbor_index = seeds[pointer]
            if not visited[neighbor_index]:
                visited[neighbor_index] = True
                neighbor_neighbors = _region_query(points, neighbor_index, eps)
                if len(neighbor_neighbors) >= min_samples:
                    for candidate in neighbor_neighbors:
                        if candidate not in seeds:
                            seeds.append(candidate)
            if labels[neighbor_index] == -1:
                labels[neighbor_index] = cluster_id
            pointer += 1

        cluster_id += 1

    return labels


def summarize_clusters(
    frame: pd.DataFrame,
    labels: np.ndarray,
    feature_columns: list[str],
) -> list[ClusterSummary]:
    labeled_frame = frame.copy()
    labeled_frame["cluster_id"] = labels
    total_rows = len(labeled_frame)
    summaries: list[ClusterSummary] = []

    for cluster_id in sorted(labeled_frame["cluster_id"].unique()):
        cluster_rows = labeled_frame[labeled_frame["cluster_id"] == cluster_id]
        numeric = cluster_rows[feature_columns].astype(float)
        summaries.append(
            ClusterSummary(
                cluster_id=int(cluster_id),
                cohort_count=int(len(cluster_rows)),
                share_of_rows=round(len(cluster_rows) / total_rows, 4),
                feature_means={column: round(float(numeric[column].mean()), 4) for column in feature_columns},
                feature_mins={column: round(float(numeric[column].min()), 4) for column in feature_columns},
                feature_maxs={column: round(float(numeric[column].max()), 4) for column in feature_columns},
            )
        )

    return summaries


def evaluate_clustering(
    points: np.ndarray,
    labels: np.ndarray,
    algorithm: Algorithm,
    inertia: float | None,
) -> EvaluationMetrics:
    cluster_labels = sorted(label for label in set(labels.tolist()) if label != -1)
    noise_count = int(np.sum(labels == -1))
    cluster_count = len(cluster_labels)
    silhouette_score = _silhouette_score(points, labels)
    davies_bouldin_score = _davies_bouldin_score(points, labels)

    return EvaluationMetrics(
        algorithm=algorithm,
        row_count=int(points.shape[0]),
        cluster_count=cluster_count,
        noise_count=noise_count,
        silhouette_score=silhouette_score,
        davies_bouldin_score=davies_bouldin_score,
        inertia=round(inertia, 6) if inertia is not None else None,
    )


def _load_frame(input_path: Path) -> pd.DataFrame:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        try:
            return pd.read_csv(input_path)
        except OSError as exc:
            raise RuntimeError(f"failed to read csv input: {input_path}") from exc
    if suffix == ".parquet":
        try:
            return pd.read_parquet(input_path)
        except OSError as exc:
            raise RuntimeError(f"failed to read parquet input: {input_path}") from exc
    raise ValueError(f"unsupported file type: {suffix or 'unknown'}")


def _validate_source_kind(source_kind: str) -> None:
    if source_kind not in {"synthetic", "deidentified"}:
        raise ValueError("clustering only accepts synthetic or deidentified data")


def _validate_columns(frame: pd.DataFrame, feature_columns: list[str]) -> None:
    if not feature_columns:
        raise ValueError("feature_columns must not be empty")

    forbidden = FORBIDDEN_COLUMNS.intersection({column.lower() for column in frame.columns})
    if forbidden:
        raise ValueError(f"input contains forbidden identifiable columns: {sorted(forbidden)}")

    missing = [column for column in feature_columns if column not in frame.columns]
    if missing:
        raise ValueError(f"missing feature columns: {missing}")

    non_numeric = [column for column in feature_columns if not pd.api.types.is_numeric_dtype(frame[column])]
    if non_numeric:
        raise ValueError(f"feature columns must be numeric: {non_numeric}")


def _standardize(points: np.ndarray) -> np.ndarray:
    means = points.mean(axis=0)
    stds = points.std(axis=0)
    stds = np.where(stds == 0, 1.0, stds)
    return (points - means) / stds


def _pairwise_distances(points: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    return np.linalg.norm(points[:, None, :] - centroids[None, :, :], axis=2)


def _region_query(points: np.ndarray, index: int, eps: float) -> list[int]:
    distances = np.linalg.norm(points - points[index], axis=1)
    return [candidate for candidate, distance in enumerate(distances) if distance <= eps]


def _silhouette_score(points: np.ndarray, labels: np.ndarray) -> float | None:
    valid_labels = [label for label in set(labels.tolist()) if label != -1]
    if len(valid_labels) < 2:
        return None

    scores: list[float] = []
    for index in range(points.shape[0]):
        label = labels[index]
        if label == -1:
            continue

        same_cluster = [candidate for candidate in range(points.shape[0]) if labels[candidate] == label and candidate != index]
        if not same_cluster:
            continue

        a = float(np.mean([np.linalg.norm(points[index] - points[candidate]) for candidate in same_cluster]))
        b_candidates = []
        for other_label in valid_labels:
            if other_label == label:
                continue
            other_members = [candidate for candidate in range(points.shape[0]) if labels[candidate] == other_label]
            if not other_members:
                continue
            b_candidates.append(
                float(np.mean([np.linalg.norm(points[index] - points[candidate]) for candidate in other_members]))
            )
        if not b_candidates:
            continue
        b = min(b_candidates)
        scores.append((b - a) / max(a, b))

    if not scores:
        return None
    return round(float(np.mean(scores)), 4)


def _davies_bouldin_score(points: np.ndarray, labels: np.ndarray) -> float | None:
    valid_labels = [label for label in sorted(set(labels.tolist())) if label != -1]
    if len(valid_labels) < 2:
        return None

    centroids: dict[int, np.ndarray] = {}
    scatters: dict[int, float] = {}
    for label in valid_labels:
        members = points[labels == label]
        centroid = members.mean(axis=0)
        centroids[label] = centroid
        scatters[label] = float(np.mean(np.linalg.norm(members - centroid, axis=1)))

    ratios: list[float] = []
    for label in valid_labels:
        candidates: list[float] = []
        for other_label in valid_labels:
            if label == other_label:
                continue
            centroid_distance = float(np.linalg.norm(centroids[label] - centroids[other_label]))
            if centroid_distance == 0:
                continue
            candidates.append((scatters[label] + scatters[other_label]) / centroid_distance)
        if candidates:
            ratios.append(max(candidates))

    if not ratios:
        return None
    return round(float(np.mean(ratios)), 4)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run aggregate-safe clustering on synthetic or deidentified cohort data.")
    parser.add_argument("--input-path", required=True, help="CSV or Parquet file containing aggregate-safe cohort rows.")
    parser.add_argument("--output-path", required=True, help="Path to write the JSON cluster summary report.")
    parser.add_argument(
        "--source-kind",
        required=True,
        choices=["synthetic", "deidentified"],
        help="Data provenance guardrail. Only synthetic or deidentified inputs are accepted.",
    )
    parser.add_argument(
        "--feature-columns",
        required=True,
        help="Comma-separated numeric feature columns used for clustering.",
    )
    parser.add_argument(
        "--algorithm",
        choices=["kmeans", "dbscan"],
        default="kmeans",
        help="Clustering algorithm to run.",
    )
    parser.add_argument("--n-clusters", type=int, default=3, help="KMeans cluster count.")
    parser.add_argument("--random-seed", type=int, default=42, help="Deterministic seed for KMeans.")
    parser.add_argument("--max-iter", type=int, default=100, help="Maximum KMeans iterations.")
    parser.add_argument("--eps", type=float, default=0.8, help="DBSCAN neighborhood radius.")
    parser.add_argument("--min-samples", type=int, default=2, help="DBSCAN minimum neighborhood size.")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    feature_columns = [column.strip() for column in args.feature_columns.split(",") if column.strip()]
    report = run_clustering_pipeline(
        input_path=args.input_path,
        output_path=args.output_path,
        source_kind=args.source_kind,
        feature_columns=feature_columns,
        algorithm=args.algorithm,
        n_clusters=args.n_clusters,
        random_seed=args.random_seed,
        max_iter=args.max_iter,
        eps=args.eps,
        min_samples=args.min_samples,
    )
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    main()
