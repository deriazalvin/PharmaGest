# Guide d'utilisation de PharmaGest

Ce guide décrit les opérations quotidiennes. Les actions affichées dépendent des
permissions du compte connecté.

## 1. Connexion

Ouvrez l'application et saisissez votre identifiant et votre mot de passe. Le
lien « Mot de passe oublié » envoie un message contenant un lien de
réinitialisation, valable une seule fois. Un administrateur peut aussi changer
le mot de passe depuis l'icône dédiée en haut à droite.

## 2. Tableau de bord

La vue d'ensemble présente les médicaments actifs, les ventes du jour, les
stocks faibles et les péremptions proches. Le sélecteur de dates filtre les
ventes et les achats sur une période. Les liens de la carte **Rapports**
téléchargent les documents PDF.

## 3. Médicaments et catégories

- **Médicaments** : la liste propose la recherche par nom, dénomination ou
  code-barres, le filtre par catégorie, le tri et la pagination.
- **Ajouter** un médicament : renseignez les champs obligatoires, le prix
  d'achat, le prix de vente et le seuil d'alerte. Une photo JPEG, PNG, WEBP ou
  GIF de 5 Mo maximum peut être jointe.
- **Modifier** : mettez à jour la fiche ; les ventes passées conservent leurs
  prix d'origine.
- **Supprimer** : un médicament utilisé dans des ventes ou des lots est
  archivé au lieu d'être effacé.
- **Catégories** : une catégorie utilisée par un médicament ne peut pas être
  supprimée.

## 4. Fournisseurs et clients

Les fiches fournisseurs conservent les coordonnées, le contact principal et le
numéro fiscal. La fiche affiche l'historique des commandes et leurs montants.
Un fournisseur lié à des achats est désactivé plutôt que supprimé.

La fiche client affiche les ventes récentes. Un client rattaché à une vente est
désactivé afin de préserver l'historique. Les ventes comptoir restent possibles
sans identification du client.

## 5. Réception d'un achat

1. Créez une commande : fournisseur, médicaments, quantités et prix d'achat.
2. La commande est enregistrée en **brouillon** : le stock ne change pas.
3. Validez la commande pour la passer en statut **commandée**.
4. À la livraison, ouvrez la commande et saisissez, pour chaque ligne, la
   quantité reçue, le numéro de lot et la date de péremption.
5. Le stock augmente une seule fois à la réception. Le statut devient
   **partiellement réceptionnée** ou **entièrement réceptionnée**.

Le bon de réception PDF est disponible depuis le détail de la commande.

## 6. Caisse et ventes

1. Ouvrez **Ventes & caisse** puis **Nouvelle vente**.
2. Ajoutez un ou plusieurs médicaments et les quantités.
3. Choisissez le client (facultatif) et le mode de paiement.
4. Validez : les lots les plus proches de la péremption sont délivrés en
   priorité (FEFO), les lots périmés ou bloqués sont ignorés.

Une quantité nulle, négative ou supérieure au stock est refusée. Un paiement
mobile reste **à vérifier** jusqu'à confirmation par un utilisateur autorisé.
Le reçu et la facture PDF sont accessibles depuis le détail de la vente.

## 7. Retours et annulations

Depuis le détail d'une vente, ouvrez la ligne concernée et choisissez
**Enregistrer** un retour : quantité, motif et remise en stock éventuelle. La
remise en stock est refusée si le lot est périmé, bloqué ou le médicament
archivé.

Une annulation globale exige un motif et réintègre le stock. Une vente avec des
retours ne peut pas être annulée. Rien n'est supprimé : chaque opération reste
tracée dans l'historique et le journal d'audit.

## 8. Stocks et inventaire

La page **Stocks & lots** liste les lots, leurs péremptions et leurs quantités.
Elle signale les lots périmés, bloqués et les prochaines péremptions.

- **Nouveau lot** : crée un lot avec son stock initial.
- **Ajuster le stock** : enregistre une variation positive ou négative avec un
  motif. Le stock ne peut jamais devenir négatif.
- **Bloquer / débloquer** un lot : un lot bloqué n'est plus vendable.

## 9. Utilisateurs et rôles

Seul un superutilisateur accède à la gestion des comptes. Il peut créer un
compte, lui affecter un ou plusieurs rôles, le modifier ou le désactiver. Un
compte ne peut pas désactiver son propre accès. Les mots de passe sont gérés
par Django et ne sont jamais stockés en clair.

## 10. Rapports

Depuis le tableau de bord, téléchargez :

- le rapport des ventes et des paiements ;
- l'état des lots et des niveaux de stock ;
- le rapport des achats ;
- la liste des produits proches de la péremption.

Chaque document reprend les références, dates, quantités, prix et totaux
calculés à partir des données réelles.

## 11. Sauvegarde

Administrateur système :

```bash
python manage.py sauvegarder_bdd
```

Conservez les fichiers produits hors du serveur et testez régulièrement une
restauration sur une copie de la base. La restauration remplace les données :
elle exige l'option `--confirm`.
