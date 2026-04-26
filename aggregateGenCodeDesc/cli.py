import argparse
import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Optional

from aggregateGenCodeDesc.logger import configure_logger, get_logger
from aggregateGenCodeDesc.loader import load_gen_code_desc_dir
from aggregateGenCodeDesc.output import (
    AGGREGATE_OUTPUT_FILENAME,
    PATCH_OUTPUT_FILENAME,
    build_aggregate_output,
)
from aggregateGenCodeDesc.metrics import AllMetrics, MetricResult, compute_all_metrics
from aggregateGenCodeDesc.alg_a import compute_alg_a_metrics, build_line_to_genratio_map
from aggregateGenCodeDesc.alg_c import compute_alg_c_metrics, stream_accumulate_surviving_set
from aggregateGenCodeDesc.blame_runner import run_git_blame_on_files, GitBlameError
from aggregateGenCodeDesc.models import GenCodeDescV2603, GenCodeDescV2604, ValidationError


EXIT_SUCCESS = 0
EXIT_RUNTIME_ERROR = 1
EXIT_VALIDATION_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aggregateGenCodeDesc",
        description="Compute AI-generated code ratio across a time window",
    )
    parser.add_argument("--repoUrl", required=True, help="Git or SVN repository URL")
    parser.add_argument("--repoBranch", required=True, help="Branch name or SVN path")
    parser.add_argument("--startTime", required=True, help="Window start (ISO 8601)")
    parser.add_argument("--endTime", required=True, help="Window end (ISO 8601)")
    parser.add_argument("--genCodeDescDir", required=True, help="Directory of genCodeDesc JSON files")
    parser.add_argument("--threshold", type=int, default=60, help="Mostly AI threshold 0-100")
    parser.add_argument("--algorithm", default="C", choices=["A", "B", "C"], help="Algorithm: A, B, or C")
    parser.add_argument("--scope", default="A", choices=["A", "B", "C", "D"], help="Scope level")
    parser.add_argument("--outputDir", default="./out", help="Output directory")
    parser.add_argument("--logLevel", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--repoPath", default=None, help="Local repo path (AlgA)")
    parser.add_argument("--commitPatchDir", default=None, help="Diff patch directory (AlgB)")
    parser.add_argument("--onMissing", default=None, help="Missing revision policy")
    parser.add_argument("--onDuplicate", default="reject", help="Duplicate revision policy")
    parser.add_argument("--onClockSkew", default="abort", help="Clock skew policy (AlgC)")
    parser.add_argument("--blameWhitespace", default="respect", choices=["respect", "ignore"])
    parser.add_argument("--renameDetection", default="basic", choices=["off", "basic", "aggressive"])
    return parser


def _collect_in_scope_files(records, scope):
    seen = set()
    for r in records:
        for df in r.DETAIL:
            fn = df.fileName
            if scope in ("A", "B"):
                ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
                source_exts = {".py", ".c", ".cc", ".cpp", ".cxx", ".go", ".h", ".hpp", ".java", ".js", ".rs", ".ts"}
                if not fn.lower().endswith(tuple(source_exts)):
                    continue
            elif scope == "C":
                doc_exts = {".md", ".rst", ".txt"}
                if not fn.lower().endswith(tuple(doc_exts)):
                    continue
            seen.add(fn)
    return sorted(seen)


def _empty_metrics() -> AllMetrics:
    return AllMetrics(
        weighted=MetricResult(value=0.0, numerator=0.0, denominator=0),
        fully_ai=MetricResult(value=0.0, numerator=0, denominator=0),
        mostly_ai=MetricResult(value=0.0, numerator=0, denominator=0, threshold=60),
    )


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logger = configure_logger(args.logLevel)

    try:
        records = load_gen_code_desc_dir(
            args.genCodeDescDir,
            expected_repo_url=args.repoUrl,
            expected_repo_branch=args.repoBranch,
        )
    except ValidationError as e:
        logger.error(str(e))
        return EXIT_VALIDATION_ERROR
    except Exception as e:
        logger.error(f"I/O error loading genCodeDescDir: {e}")
        return EXIT_RUNTIME_ERROR

    if not records:
        logger.info("No genCodeDesc records found in directory")
        return EXIT_SUCCESS

    try:
        if args.algorithm == "C":
            surviving, warnings = stream_accumulate_surviving_set(
                str(Path(args.genCodeDescDir)),
                end_time=args.endTime,
                return_warnings=True,
            )
            in_window = [
                s for s in surviving
                if args.startTime <= s.blame_timestamp <= args.endTime
            ]
            gen_ratios = [s.gen_ratio for s in in_window]
            metrics = compute_all_metrics(gen_ratios, args.threshold)

        elif args.algorithm == "A":
            v2603_records = [r for r in records if isinstance(r, GenCodeDescV2603)]
            genratio_map = build_line_to_genratio_map(v2603_records)

            repo_path = args.repoPath
            cleanup_clone = None
            if not repo_path and args.repoUrl and (
                args.repoUrl.startswith("http://") or args.repoUrl.startswith("https://") or
                args.repoUrl.startswith("git@") or args.repoUrl.startswith("ssh://")
            ):
                import tempfile
                clone_dir = Path(tempfile.mkdtemp(prefix="aggregateGenCode_"))
                cleanup_clone = clone_dir
                logger.info(f"Auto-cloning {args.repoUrl} to {clone_dir}")
                r = subprocess.run(["git", "clone", args.repoUrl, str(clone_dir)],
                                 capture_output=True, text=True, timeout=600)
                if r.returncode != 0:
                    logger.error(f"Clone failed: {r.stderr.strip()}")
                    return EXIT_RUNTIME_ERROR
                repo_path = str(clone_dir)
            elif not repo_path:
                repo_path = args.repoUrl

            in_scope_files = _collect_in_scope_files(records, args.scope)

            rename_detection = args.renameDetection
            ignore_whitespace = args.blameWhitespace == "ignore"

            try:
                blame_lines = run_git_blame_on_files(
                    repo_path,
                    in_scope_files,
                    ignore_whitespace=ignore_whitespace,
                    rename_detection=rename_detection,
                )
            except (GitBlameError, FileNotFoundError) as e:
                logger.error(str(e))
                return EXIT_RUNTIME_ERROR
            finally:
                if cleanup_clone:
                    import shutil
                    shutil.rmtree(cleanup_clone, ignore_errors=True)

            if not blame_lines:
                gen_ratios = []
                metrics = _empty_metrics()
                warnings = [f"No in-scope files found for blame in {repo_path}"]
            else:
                result = compute_alg_a_metrics(
                    blame_lines=blame_lines,
                    genratio_map=genratio_map,
                    start_time=args.startTime,
                    end_time=args.endTime,
                    threshold=args.threshold,
                )
                metrics = result.metrics
                warnings = []
                gen_ratios = [l.gen_ratio for l in result.in_window_lines]

        elif args.algorithm == "B":
            v2603_records = [r for r in records if isinstance(r, GenCodeDescV2603)]
            from aggregateGenCodeDesc.alg_b import compute_alg_b_metrics
            from aggregateGenCodeDesc.vcs_ordering import get_ordered_patch_sequence, load_ordered_patches, get_git_commit_order
            from aggregateGenCodeDesc.alg_a import BlameLine

            repo_path = args.repoPath or args.repoUrl
            if not args.commitPatchDir:
                logger.error("--commitPatchDir is required for Algorithm B")
                return EXIT_VALIDATION_ERROR

            try:
                ordered_commits = get_git_commit_order(repo_path, args.repoBranch, args.startTime, args.endTime)
                patch_seq = load_ordered_patches(args.commitPatchDir, ordered_commits)
                diff_seq = [(text, rev_id, "") for text, rev_id in patch_seq]
            except Exception as e:
                logger.error(f"Failed to load patches: {e}")
                return EXIT_RUNTIME_ERROR

            result = compute_alg_b_metrics(
                diff_seq, v2603_records, args.startTime, args.endTime, args.threshold,
            )
            metrics = result.metrics
            warnings = []
            gen_ratios = [l.gen_ratio for l in result.in_window_lines]
        else:
            logger.error(f"Unknown algorithm: {args.algorithm}")
            return EXIT_VALIDATION_ERROR

    except ValidationError as e:
        logger.error(str(e))
        return EXIT_VALIDATION_ERROR
    except Exception as e:
        logger.error(f"Runtime error: {e}")
        return EXIT_RUNTIME_ERROR

    output_dir = Path(args.outputDir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output = build_aggregate_output(
        repo_url=args.repoUrl,
        repo_branch=args.repoBranch,
        start_time=args.startTime,
        end_time=args.endTime,
        algorithm=args.algorithm,
        scope=args.scope,
        threshold=args.threshold,
        input_protocol_version="26.04" if args.algorithm == "C" else "26.03",
        metrics=metrics,
        warnings=warnings,
        gen_ratios=gen_ratios,
        detail_files=[],
    )

    json_path = output_dir / AGGREGATE_OUTPUT_FILENAME
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    patch_path = output_dir / PATCH_OUTPUT_FILENAME
    patch_path.write_text(
        f"# aggregateGenCodeDesc patch\n"
        f"# repoURL={args.repoUrl} repoBranch={args.repoBranch}\n"
        f"# startTime={args.startTime} endTime={args.endTime}\n"
        f"# algorithm={args.algorithm} scope={args.scope}\n"
        f"# aggregate:{args.startTime}..{args.endTime}\n"
    )

    logger.info(
        f"SUMMARY aggregate totalLines={len(gen_ratios)} "
        f"weighted={metrics.weighted.value:.1%} "
        f"fullyAI={metrics.fully_ai.value:.1%} "
        f"mostlyAI={metrics.mostly_ai.value:.1%}"
    )

    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
