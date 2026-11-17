from datetime import datetime
from pathlib import Path
import sqlite3

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Crée une copie cohérente de la base SQLite dans le dossier backups/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            help="Chemin du fichier de sauvegarde à créer.",
        )

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError(
                "Cette commande ne prend en charge que les bases SQLite."
            )
        target = (
            Path(options["output"]).expanduser()
            if options.get("output")
            else self._default_path()
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        connection.ensure_connection()
        with sqlite3.connect(target) as destination:
            connection.connection.backup(destination)
        self.stdout.write(
            self.style.SUCCESS(f"Sauvegarde créée : {target}")
        )

    def _default_path(self):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return Path(settings.BASE_DIR) / "backups" / f"pharmagest-{stamp}.sqlite3"
