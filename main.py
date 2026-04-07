from invest_notify.cli import build_parser, run_fetch, run_notify, run_once, run_plot
from invest_notify.settings import load_app_settings
from invest_notify.utils.logger import setup_logger


def main() -> None:
    app = load_app_settings()
    setup_logger(level=app.log_level)

    parser = build_parser()
    args = parser.parse_args()

    match args.command:
        case "fetch":
            run_fetch()
        case "plot":
            run_plot()
        case "notify":
            run_notify()
        case "run-once":
            run_once()
        case _:
            parser.print_help()


if __name__ == "__main__":
    main()
