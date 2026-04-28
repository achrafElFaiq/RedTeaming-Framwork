"""
RedTrace — Red Teaming Framework CLI
=====================================

Usage::

    python main.py <campaign.yaml>
    python main.py campaigns/smoke_test.yaml --log-level DEBUG
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

from core.application.campaign_loader import load_campaign
from core.models.attack_target import AttackTarget
from core.orchestration.attack_orchestrator import AttackOrchestrator

DASHBOARD_PATH = Path(__file__).resolve().parent / "core" / "results" / "report_viewer.py"


def _configure_logging(level: str) -> None:
    """Set up framework logging and silence noisy third-party loggers."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    for noisy in (
        "pyrit.memory", "pyrit.prompt_target", "pyrit.executor",
        "pyrit.score", "pyrit.exceptions",
        "httpx", "httpcore", "asyncio",
    ):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # Replace verbose PyRIT scorer retry errors with a one-liner
    logging.getLogger("pyrit.exceptions.exceptions_helpers").addFilter(_ScorerRetryFilter())


class _ScorerRetryFilter(logging.Filter):
    """Collapse PyRIT scorer retry stack traces into a single readable line."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "objective scorer" in msg and "Invalid JSON" in msg:
            attempt = "?"
            if "Retry attempt " in msg:
                attempt = msg.split("Retry attempt ")[1].split(" ")[0]
            record.msg = (
                "[Scorer] ⚠ Retry #%s — LLM returned invalid JSON "
                "(scorer model may not support structured output reliably)"
            )
            record.args = (attempt,)
        return True


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="redtrace",
        description="Run a red teaming campaign from a YAML configuration file.",
    )
    parser.add_argument(
        "campaign",
        help="Path to the campaign YAML file (e.g. campaigns/smoke_test.yaml)",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    parser.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Skip automatic dashboard launch after the campaign",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging(args.log_level)

    logger = logging.getLogger("redtrace")

    # ── Load campaign ──────────────────────────────────────────
    try:
        config = load_campaign(args.campaign)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load campaign: %s", exc)
        return 1

    logger.info("─" * 60)
    logger.info("[Config] Campaign  : %s", args.campaign)
    logger.info("[Config] Target    : %s → %s", config.target_name, config.target_url)
    logger.info("[Config] Attacks   : %d", len(config.active_attacks))
    for i, atk in enumerate(config.active_attacks, 1):
        mode = atk.config.get("orchestrator", atk.config.get("probe", "?"))
        logger.info("[Config]   %d. [%s] %s (%s)", i, atk.framework, atk.intent, mode)
    logger.info("─" * 60)

    # ── Build orchestrator ─────────────────────────────────────
    target = AttackTarget(config.target_name, config.target_url)
    orchestrator = AttackOrchestrator(
        target=target,
        use_case_doc_path=config.use_case_doc_path or None,
    )
    for attack in config.active_attacks:
        orchestrator.add_attack(attack)

    # ── Execute ────────────────────────────────────────────────
    orchestrator.execute_attacks()

    # ── Summary ────────────────────────────────────────────────
    summary = orchestrator.summary()
    print("\n" + "=" * 60)
    print("  CAMPAIGN SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    print("=" * 60)

    if orchestrator.has_execution_errors or orchestrator.has_failures:
        exit_code = 1
    else:
        exit_code = 0

    # ── Launch dashboard ──────────────────────────────────────
    if not args.no_dashboard:
        _launch_dashboard(logger)

    return exit_code


def _launch_dashboard(logger: logging.Logger) -> None:
    """Launch the Streamlit dashboard in a subprocess."""
    logger.info("─" * 50)
    logger.info("[Dashboard] Lancement du dashboard RedTrace...")
    logger.info("[Dashboard] URL : http://localhost:8501")
    logger.info("─" * 50)
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(DASHBOARD_PATH)],
            check=False,
        )
    except KeyboardInterrupt:
        logger.info("[Dashboard] Dashboard arrêté par l'utilisateur")
    except FileNotFoundError:
        logger.error(
            "[Dashboard] Streamlit n'est pas installé. "
            "Installez-le avec : pip install streamlit"
        )


if __name__ == "__main__":
    sys.exit(main())
