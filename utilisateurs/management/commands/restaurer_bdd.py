from pathlib import Path
import sqlite3

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

SQLITE_HEADER = b"SQLite format 3\x00"


class Command(BaseCommand):
    help = "Restaure la base SQLite depuis un fichier de sauvegarde."

    def add_arguments(self, parser):
        parser.add_argument("sauvegarde", help="Fichier de sauvegarde à restaurer.")
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Confirme le remplacement des données actuelles.",
        )

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError(
                "Cette commande ne prend en charge que les bases SQLite."
            )
        source = Path(options["sauvegarde"]).expanduser()
        if not source.is_file():
            raise CommandError(f"Sauvegarde introuvable : {source}")
        with source.open("rb") as handle:
            if handle.read(len(SQLITE_HEADER)) != SQLITE_HEADER:
                raise CommandError(
                    "Le fichier fourni n'est pas une base SQLite valide."
                )
        if not options["confirm"]:
            raise CommandError(
                "Cette opération remplace les données actuelles. "
                "Relancez avec --confirm après avoir sauvegardé la base en cours."
            )
        connection.ensure_connection()
        with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as backup:
            backup.backup(connection.connection)
        self.stdout.write(
            self.style.SUCCESS(f"Base restaurée depuis : {source}")
        )
