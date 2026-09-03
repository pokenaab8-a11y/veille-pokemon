# 🚀 Tuto d'installation — Bot de veille cartes Pokémon

Suis les étapes **dans l'ordre**. Compte ~20-25 min la première fois. Aucune ligne de code
à écrire : tu crées des comptes gratuits et tu colles des clés. Coche au fur et à mesure.

**Ce que tu vas mettre en place :**
1. Un bot Telegram (pour recevoir les alertes)
2. Des clés eBay (pour lire les annonces)
3. Un dépôt GitHub qui fait tourner le bot gratuitement, tout seul

> 💡 **Les cotes Cardmarket viennent de tcgdex.dev — gratuit et SANS clé.** Rien à créer de
> ce côté. (pokemontcg.io, devenu le service payant Scrydex, n'est PAS utilisé ; il sert
> juste de secours automatique, sans clé.)

Garde un bloc-notes ouvert pour y coller les clés au fur et à mesure. Tu en auras **4**.

---

## ✅ Étape 1 — Créer le bot Telegram (~5 min)

1. [ ] Ouvre Telegram, cherche **@BotFather** (celui avec la coche bleue), ouvre-le.
2. [ ] Envoie `/newbot`.
3. [ ] Donne un **nom** (ex. « Ma veille Pokémon »).
4. [ ] Donne un **identifiant** qui finit par `bot` (ex. `ma_veille_pkmn_bot`).
5. [ ] BotFather te renvoie un **token** genre `123456789:AAE-xxxxxxxxxxxxxxxxx`.
   👉 **Colle-le dans ton bloc-notes = `TELEGRAM_TOKEN`.**
6. [ ] **Clique sur ton nouveau bot et appuie sur « Démarrer » / « Start ».**
   ⚠️ Obligatoire, sinon il ne pourra pas t'écrire.

### Récupérer ton chat_id
7. [ ] Dans Telegram, cherche **@userinfobot**, ouvre-le, appuie sur « Start ».
8. [ ] Il te répond avec un numéro (ex. `987654321`).
   👉 **Colle ce numéro = `TELEGRAM_CHAT_ID`.**

---

## ✅ Étape 2 — Créer tes clés eBay (API officielle Browse) (~10 min)

1. [ ] Va sur **developer.ebay.com**, clique **Register** / « S'inscrire » (gratuit).
2. [ ] Confirme ton email et connecte-toi.
3. [ ] En haut, va dans **Hi, [ton nom] → Application Keysets**
   (ou « Your Account → Application Keysets »).
4. [ ] Dans la colonne **Production** (⚠️ pas Sandbox), clique **Create a keyset**
   si besoin, accepte les conditions.
5. [ ] Note ces deux valeurs :
   - **App ID (Client ID)** 👉 **= `EBAY_CLIENT_ID`**
   - **Cert ID (Client Secret)** 👉 **= `EBAY_CLIENT_SECRET`**

> Pas besoin du Dev ID ni de tokens : le bot se débrouille tout seul avec ces deux clés.

**À ce stade ton bloc-notes doit contenir 4 valeurs :**
`TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`.

---

## ✅ Étape 3 — Mettre le bot sur GitHub (~5 min)

1. [ ] Crée un compte sur **github.com** (gratuit) si tu n'en as pas.
2. [ ] En haut à droite, **＋ → New repository**.
3. [ ] Donne un nom (ex. `veille-pokemon`), choisis **Public**
   (⚠️ important : Public = minutes gratuites illimitées), puis **Create repository**.
4. [ ] Sur la page du dépôt vide : **Add file → Upload files**.
5. [ ] Fais **glisser tous les fichiers du dossier** que je t'ai donné (y compris le
   dossier `.github`) dans la zone d'upload.
6. [ ] En bas, clique **Commit changes**.

> Tu dois voir : `bot.py`, `watchlist.json`, `discovery.json`, `requirements.txt`,
> le dossier `.github/workflows/watch.yml`, et les README/TUTO.

---

## ✅ Étape 4 — Coller tes secrets (~4 min)

1. [ ] Dans le dépôt : **Settings** (onglet en haut).
2. [ ] Menu de gauche : **Secrets and variables → Actions**.
3. [ ] Clique **New repository secret** et crée-les **un par un**
   (le **nom doit être exactement** celui-ci) :

| Name (exact)          | Secret (ta valeur)         |
|-----------------------|----------------------------|
| `EBAY_CLIENT_ID`      | App ID eBay                |
| `EBAY_CLIENT_SECRET`  | Cert ID eBay               |
| `TELEGRAM_TOKEN`      | token BotFather            |
| `TELEGRAM_CHAT_ID`    | ton numéro (@userinfobot)  |

4. [ ] Vérifie que tu as bien **4 secrets** listés.

> Le secret `POKEMONTCG_API_KEY` n'est **pas nécessaire** (on est sur tcgdex). Tu peux
> l'ignorer. Le bot fonctionne sans.

---

## ✅ Étape 5 — Régler tes critères (~3 min)

1. [ ] Dans le dépôt, ouvre **`discovery.json`**, clique le crayon ✏️ (Edit).
2. [ ] Vérifie ces valeurs :
   - `"price_source": "tcgdex"` ← déjà réglé, la source gratuite sans clé.
   - `min_discount_pct` : `30` = alerte si prix ≤ 70 % de la cote. Ton curseur principal.
   - `min_reference_eur` : `10` = ignore les cartes qui cotent moins de 10 €.
   - `min_price` : `7` (ton plancher d'annonce).
3. [ ] **Commit changes** en bas.

> Tu pourras retoucher ça quand tu veux, de la même façon.

---

## ✅ Étape 6 — Lancer et tester (~5 min)

1. [ ] Onglet **Actions** du dépôt. Si un bandeau demande d'activer les workflows,
   clique **I understand my workflows, go ahead and enable them**.
2. [ ] À gauche, clique le workflow **« Veille cartes Pokemon »**.
3. [ ] À droite, bouton **Run workflow → Run workflow** (lancement manuel).
4. [ ] Attends ~1 min, rafraîchis. Clique sur la ligne d'exécution pour voir les **logs**.
   - ✅ Pastille verte = ça a tourné.
   - ❌ Pastille rouge = ouvre les logs, regarde le message (voir Dépannage plus bas).
5. [ ] Ensuite, **ça tourne tout seul toutes les 20 minutes.**

### Astuce : forcer une alerte pour vérifier que tout marche
Le bot est exigeant (il n'alerte que sur de vraies affaires), donc tu peux ne rien
recevoir au 1er essai — c'est normal. Pour tester le circuit **et** confirmer que les cotes
tcgdex remontent bien :

1. [ ] Édite `discovery.json` : mets temporairement `min_discount_pct` à `1` et
   `min_reference_eur` à `1`. Commit.
2. [ ] Relance le workflow (Étape 6.3). Tu devrais recevoir des alertes montrant une
   **« Cote Cardmarket : X € »** → preuve que tcgdex fonctionne.
3. [ ] **Remets ensuite tes vraies valeurs** (`30` et `10`) et commit.

---

## 🛠️ Dépannage (les erreurs courantes)

- **Log rouge « KeyError: 'EBAY_CLIENT_ID' » (ou un autre nom)** → un secret manque ou
  son nom est mal orthographié. Retourne à l'Étape 4, vérifie l'orthographe exacte.
- **Erreur eBay 401 / invalid_client** → App ID ou Cert ID incorrect, ou tu as pris les
  clés **Sandbox** au lieu de **Production**. Reprends l'Étape 2.
- **Telegram « chat not found » / « bot was blocked »** → tu n'as pas appuyé sur
  « Start » dans ton bot (Étape 1.6), ou le `TELEGRAM_CHAT_ID` est faux.
- **Les alertes de test n'affichent pas de cote** → tcgdex n'a pas trouvé la carte pour
  ces annonces (titre sans numéro, carte trop récente, ou set non couvert). Le bot bascule
  seul sur pokemontcg.io en secours. Si le souci persiste, dis-le-moi avec un exemple d'annonce.
- **Aucune alerte mais log vert** → normal : pas d'affaire détectée sur ce passage.
  Utilise l'astuce de test ci-dessus pour confirmer que tout est branché.
- **Le workflow ne se lance plus après ~2 mois** → GitHub met en pause les tâches
  planifiées si le dépôt est inactif. Fais un petit commit pour le réveiller.

---

## 🎚️ Après le lancement — régler le tir

- **Trop d'alertes ?** monte `min_discount_pct` (40, 50) et/ou `min_reference_eur`.
- **Pas assez ?** baisse-les, et baisse `min_price` (une carte à 5 € qui cote 25 €
  reste une affaire).
- **Trop de bruit d'un type d'annonce ?** ajoute des mots dans `exclude_keywords`.
- **Ne viser que les cartes à l'unité ?** renseigne `category_ids` (l'ID est dans
  l'URL eBay quand tu navigues dans la catégorie « Cartes Pokémon à l'unité »).

---

## 📋 Récap express

- [ ] Bot Telegram créé + « Start » appuyé + chat_id récupéré
- [ ] Clés eBay Production (App ID + Cert ID)
- [ ] Dépôt GitHub public + fichiers uploadés
- [ ] 4 secrets créés (noms exacts)
- [ ] `discovery.json` réglé (`price_source` = tcgdex)
- [ ] Workflow activé + testé (pastille verte + alerte de test avec une cote affichée)

Une fois tout coché, tu n'as plus rien à faire : le bot veille pour toi. 🎉

---

> ℹ️ **Source des prix.** Par défaut le bot lit les cotes Cardmarket (en €) sur
> **tcgdex.dev** — gratuit, sans clé, sans compte. pokemontcg.io sert de secours
> automatique. Si un jour tu veux l'inverse, change `"price_source"` dans `discovery.json`.
