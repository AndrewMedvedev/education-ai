import argparse
import asyncio
import logging
import sys

from .commands import create_default_organization, create_first_admin, create_permissions


def main() -> None:
    """Запускает сценарий модуля и связывает подготовку данных с основным действием."""
    parser = argparse.ArgumentParser(description="CLI утилиты для diocon-tickets")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Команда `create-first-admin`
    subparsers.add_parser("create-first-admin", help="Создать первого администратора")
    subparsers.add_parser(
        "create-default-organization",
        help="Создать системную организацию и назначить первого администратора",
    )
    subparsers.add_parser("create-permissions", help="Создать permissions")

    # Команда `init-s3-storage`
    subparsers.add_parser("init-s3-buckets", help="Инициализация S3 хранилища")

    args = parser.parse_args()

    if args.command == "create-permissions":
        asyncio.run(create_permissions())

    elif args.command == "create-first-admin":
        asyncio.run(create_first_admin())

    elif args.command == "create-default-organization":
        asyncio.run(create_default_organization())

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
