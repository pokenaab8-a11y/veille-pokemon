# Bot de veille cartes Pokémon → Telegram

Surveille eBay (annonces actives) et t'envoie une alerte Telegram. Deux modes qui
tournent ensemble :

- **Watch-list** (`watchlist.json`) : des cartes précises que tu choisis → alerte sur
  la vraie décote vs cote Cardmarket. Précis, peu de bruit.
- **Détecteur d'affaires** (`discovery.json`) : scanne large, **identifie** chaque carte
  via son numéro de collection (ex. 199/165), récupère sa cote Cardmarket, et n'alerte
  **que si l'annonce est nettement sous la cote**. Silence sur tout le reste. Il ignore
  ce qu'il ne peut pas identifier (titres vagues, gradées) — précision avant exhaustivité.

**100 % gratuit à faire tourner.** Aucune ligne de code à écrire : tu crées 3 comptes
gratuits, tu colles quelques clés, tu remplis ta liste de cartes. Compte ~20-30 min
la première fois.

---

## Ce dont tu as besoin (tout gratuit)

1. Un compte **Telegram**
2. Un compte **eBay Developers** (gratuit)
3. Un compte **GitHub** (gratuit)
4. *(Optionnel)* une clé **pokemontcg.io** pour le mode « cote Cardmarket auto »

---

## Étape 1 — Créer ton bot Telegram

1. Dans Telegram, ouvre une conversation avec **@BotFather**.
2. Envoie `/newbot`, choisis un nom et un identifiant. BotFather te donne un
   **token** du type `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxx`. Garde-le.
3. **Ouvre ton nouveau bot et appuie sur « Démarrer »** (obligatoire, sinon il ne
   pourra pas t'écrire).
4. Récupère ton **chat_id** : ouvre une conversation avec **@userinfobot**, il te
   renvoie un numéro (ex. `987654321`). C'est ton `TELEGRAM_CHAT_ID`.

---

## Étape 2 — Créer tes clés eBay (API officielle Browse)

1. Va sur **developer.ebay.com**, crée un compte (gratuit), connecte-toi.
2. Dans **Application Keysets**, crée un keyset **Production**.
3. Note deux valeurs :
   - **App ID (Client ID)** → ce sera `EBAY_CLIENT_ID`
   - **Cert ID (Client Secret)** → ce sera `EBAY_CLIENT_SECRET`

> Pas besoin d'autre chose : le bot demande un jeton tout seul à chaque exécution.
> Quota par défaut : 5 000 requêtes/jour, largement suffisant.

---

## Étape 3 — (Optionnel) clé pokemontcg.io pour la cote Cardmarket

Sur **dev.pokemontcg.io**, demande une clé API gratuite → `POKEMONTCG_API_KEY`.
Sans clé, le mode « cote auto » fonctionne quand même mais avec un quota plus bas ;
tu peux aussi t'en passer et utiliser `reference_eur` / `max_price` à la main.

---

## Étape 4 — Mettre le projet sur GitHub

1. Crée un **nouveau dépôt** GitHub. Choisis **Public** (Actions gratuit et illimité).
2. Envoie-y tous les fichiers de ce dossier (glisser-déposer via « Add file » →
   « Upload files » suffit, y compris le dossier `.github`).

---

## Étape 5 — Coller tes secrets

Dans le dépôt : **Settings → Secrets and variables → Actions → New repository secret**.
Crée un secret pour chaque valeur (le nom doit être exact) :

| Nom du secret          | Valeur                                   |
|------------------------|------------------------------------------|
| `EBAY_CLIENT_ID`       | App ID eBay                              |
| `EBAY_CLIENT_SECRET`   | Cert ID eBay                            |
| `TELEGRAM_TOKEN`       | token BotFather                         |
| `TELEGRAM_CHAT_ID`     | ton numéro (@userinfobot)              |
| `POKEMONTCG_API_KEY`   | clé pokemontcg.io (ou laisse vide)     |

---

## Étape 6 — Remplir ta liste de cartes

Édite **`watchlist.json`** directement sur GitHub (crayon ✏️). Trois modes possibles
par carte :

- **Cote auto** : `pokemontcg_id` + `threshold_pct` → alerte si prix ≤ X % de la cote
  Cardmarket. Pour trouver l'`id` d'une carte : `https://api.pokemontcg.io/v2/cards?q=name:charizard`
  (le champ `id`, ex. `sv3pt5-199`). **Vérifie l'id**, les exemples fournis sont
  à ajuster.
- **Référence manuelle** : `reference_eur` + `threshold_pct` → tu fixes la cote toi-même.
- **Prix max direct** : `max_price` → alerte dès qu'une annonce passe sous ce prix.

`ebay_query` = les mots-clés tapés dans la barre eBay. Sois précis (numéro de carte,
set) pour éviter le bruit.

---

## Étape 7 — Lancer et vérifier

1. Onglet **Actions** du dépôt → autorise les workflows si demandé.
2. Ouvre **« Veille cartes Pokemon »** → **Run workflow** (lancement manuel).
3. Regarde les logs. Si tout va bien, tu reçois les alertes sur Telegram.
4. Ensuite ça tourne **tout seul toutes les 20 min**.

---

## Bon à savoir

- **Premier lancement bavard** : il peut y avoir plusieurs alertes d'un coup
  (tout est « nouveau »). Ensuite seules les vraies nouveautés déclenchent.
- **Fréquence** : change le `cron` dans `.github/workflows/watch.yml`
  (`*/15 * * * *` = 15 min). Les horaires GitHub peuvent avoir quelques minutes
  de retard aux heures de pointe, c'est normal.
- **Repo actif** : GitHub désactive les tâches planifiées après ~60 jours sans
  activité sur le dépôt. Un commit de temps en temps (ou le bot qui sauvegarde
  `seen.json`) suffit à le garder vivant.
- **Ajuster tes seuils** : commence prudent (60-70 % de la cote) pour ne garder
  que les vraies affaires, puis affine.

---

## Le mode Détecteur d'affaires (`discovery.json`)

Ne t'alerte **que** quand une carte est nettement sous sa cote. Fonctionnement : le bot
lit le **numéro de collection** dans le titre (ex. `199/165`), retrouve la carte sur
pokemontcg.io, récupère sa **cote Cardmarket (€)**, et compare au prix demandé.

Réglages :

- `min_discount_pct` : décote minimale pour déclencher. `30` = alerte si prix ≤ 70 % de
  la cote. **C'est ton curseur principal** : monte-le (40, 50) pour n'avoir que les grosses affaires.
- `min_reference_eur` : ignore les cartes dont la cote est sous ce montant (pas de marge).
  Astuce : c'est un meilleur filtre « ça vaut le coup » que le prix de l'annonce lui-même.
- `min_price` : prix mini de l'annonce (tu avais dit 7 €). Tu peux le baisser : une carte
  à 5 € qui cote 25 € reste une belle affaire.
- `skip_graded` : `true` ignore les cartes gradées PSA/CGC/BGS (non comparables à la cote brute).
- `max_lookups_per_run` : plafond d'identifications par passage, pour protéger ton quota API.
- `category_ids`, `exclude_keywords` : comme avant, pour cadrer la recherche.

### Ce que ça capte — et ce que ça rate (honnêteté)

- ✅ Il juge les annonces qui **contiennent le numéro** de la carte (le cas des vrais singles).
- ❌ Il **ignore volontairement** ce qu'il ne peut pas identifier (titres vagues, sans numéro)
  et les cartes gradées. C'est le prix du « seulement les affaires » : précision > exhaustivité.
- ⚠️ La cote = état **correct**. Une carte très en dessous peut être **abîmée** : les photos
  restent à vérifier. Le bot te le rappelle dans chaque alerte.
- ⚠️ Rare cas d'homonymie de numéro entre langues/sets : le bot recoupe avec le nom du titre,
  mais garde un œil critique.

### Source des prix : pokemontcg.io ou tcgdex (champ `price_source`)

⚠️ **À savoir :** pokemontcg.io est devenu **Scrydex**, qui est **payant** (à partir de
29 $/mois, pas de palier gratuit). On ne l'utilise donc **pas**. pokemontcg.io reste
gratuit et fonctionnel pour l'instant, mais finira par fermer.

Le bot gère deux sources gratuites, réglables via `price_source` dans `discovery.json` :

- `"tcgdex"` *(défaut)* : **tcgdex.dev**. Gratuit, **sans aucune clé**, prix Cardmarket
  en EUR. C'est la source par défaut : aucun compte à créer.
- `"pokemontcg"` : pokemontcg.io. Gratuit aussi — 1000 requêtes/jour sans clé, 20 000 avec
  la clé gratuite (`POKEMONTCG_API_KEY`). Utilisable en secours.

Le bot **bascule automatiquement** vers l'autre source si la source primaire tombe en panne
(pokemontcg.io sert donc de filet de secours, et fonctionne aussi sans clé).

---

## Évolutions possibles (plus tard)

- Ajouter eBay Allemagne/UK (souvent moins cher) via `EBAY_MARKETPLACE`.
- Filtrer par état/vendeur, ignorer les lots.
- Ajouter Vinted / Leboncoin — mais ça sort du gratuit (proxies résidentiels
  nécessaires face à leurs anti-bots) et de l'API officielle.
