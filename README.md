# PharmaGest

Application web de gestion de pharmacie développée avec Django. Elle couvre le
catalogue de médicaments, les lots et péremptions, les achats et réceptions, la
caisse, les retours, les utilisateurs et les rapports PDF.

## Fonctionnalités

- Authentification, rôles et permissions Django, journal d'audit.
- CRUD des médicaments avec photo, catégories, prix et seuil d'alerte.
- Fournisseurs et clients avec historique des opérations.
- Commandes d'achat, réceptions partielles ou complètes, lots et péremptions.
- Caisse avec recherche, panier, paiement et sortie de stock FEFO.
- Retours et annulations traçables, remboursements à confirmer.
- Tableau de bord, statistiques et documents PDF (reçu, facture, bons, rapports).
- Sauvegarde et restauration de la base SQLite.

## Technologies

Python, Django, SQLite, CSS responsive maison, Pillow, ReportLab.

## Installation

Prérequis : Python 3.10 ou plus récent.

```bash
git clone https://github.com/deriazalvin/PharmaGest.git
cd PharmaGest
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

L'application est disponible sur <http://127.0.0.1:8000/> et redirige vers la
page de connexion. L'administration Django reste accessible sur `/admin/`.

### Données de démonstration

```bash
python manage.py charger_donnees_demo
```

La commande crée un catalogue, des lots, une commande d'achat et une vente.
Elle est rejouable sans dupliquer les données. Le compte `demo` créé ne possède
pas de mot de passe utilisable : connectez-vous avec votre superutilisateur.

### Rôles par défaut

Les groupes **Pharmacien responsable**, **Gestionnaire de stock**, **Caissier**
et **Responsable de gestion** sont créés à la première ouverture de la page
Utilisateurs. Un superutilisateur peut ensuite affecter un ou plusieurs rôles à
chaque compte.

## Configuration

Les paramètres sensibles sont lus dans des variables d'environnement.

| Variable | Rôle | Défaut |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Clé secrète | valeur de développement |
| `DJANGO_DEBUG` | Mode debug (`1`/`0`) | `1` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules | `localhost,127.0.0.1` |
| `PHARMAGEST_DB_PATH` | Chemin de la base SQLite | `db.sqlite3` |
| `DJANGO_DEFAULT_FROM_EMAIL` | Expéditeur des e-mails | `pharmagest@example.test` |
| `DJANGO_EMAIL_BACKEND` | Backend Django d'envoi | console en dev, SMTP en production |
| `DJANGO_EMAIL_HOST` / `DJANGO_EMAIL_PORT` | Serveur SMTP | `localhost` / `25` |
| `DJANGO_EMAIL_HOST_USER` / `DJANGO_EMAIL_HOST_PASSWORD` | Identifiants SMTP | vide |
| `DJANGO_EMAIL_USE_TLS` | TLS SMTP (`1`/`0`) | `0` |

En production, définissez impérativement `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`
et `DJANGO_ALLOWED_HOSTS`. Le mode production active la redirection HTTPS, les
cookies sécurisés et HSTS.

## Tests

```bash
python manage.py test
```

Les tests couvrent les modèles, les formulaires, les permissions, les calculs,
le FEFO, les réceptions, les ventes, les retours, les PDF et la sauvegarde.

## Sauvegarde et restauration

```bash
python manage.py sauvegarder_bdd
# ou vers un chemin précis
python manage.py sauvegarder_bdd --output /chemin/sauvegarde.sqlite3

python manage.py restaurer_bdd backups/pharmagest-AAAAMMJJ-HHMMSS.sqlite3 --confirm
```

Les sauvegardes sont écrites dans `backups/` (ignoré par Git). La restauration
vérifie l'en-tête SQLite et exige `--confirm`, car elle remplace les données en
cours. Testez la restauration sur une copie avant toute mise en production.

## Structure

```
PharmaGest/
├── config/          # settings, URLs, utilitaires partagés
├── utilisateurs/    # comptes, rôles, audit, sauvegarde, données de démo
├── medicaments/     # catalogue et photos
├── categories/
├── fournisseurs/
├── clients/
├── achats/          # commandes, réceptions, lignes
├── stock/           # lots, mouvements, inventaire
├── ventes/          # caisse, paiements, retours
├── rapports/        # tableau de bord et PDF
├── templates/       # gabarits partagés et authentification
├── static/          # CSS et JavaScript
├── media/           # photos téléversées
└── docs/            # guide d'utilisation et dossier de conception
```

## Documentation

- [Guide d'utilisation](docs/GUIDE_UTILISATION.md)
- [Dossier de conception](docs/CONCEPTION.md)
