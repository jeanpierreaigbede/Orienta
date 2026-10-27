# Orienta

Assistant de pré-orientation santé pour les ONG, construit pour la démonstration **« Implémenter le chiffrement dans les workflows d'IA »** (Encrypted by Design 2026, Bénin & Togo).

Un patient décrit ses symptômes. L'assistant (un modèle d'IA appelé via [RodiumAI](https://pypi.org/project/rodiumai/)) pose quelques questions, puis l'oriente vers l'un de trois niveaux de soins : urgence, consultation sous 48 heures ou conseils à domicile. Les patients orientés en urgence apparaissent dans la liste de rappel des agents de santé.

> Orienta ne pose aucun diagnostic et ne remplace pas un professionnel de santé. N'utilisez que des données fictives tant que le projet n'a pas été validé par un soignant et autorisé par l'APDP (Bénin) ou l'IPDCP (Togo).

---

## Sommaire

1. [Les trois branches](#1-les-trois-branches)
2. [Structure du dépôt](#2-structure-du-dépôt)
3. [Prérequis](#3-prérequis)
4. [Installation de A à Z](#4-installation-de-a-à-z)
5. [Premier parcours complet](#5-premier-parcours-complet)
6. [Changer de branche](#6-changer-de-branche)
7. [Faire la démonstration avant / après](#7-faire-la-démonstration-avant--après)
8. [Rotation de la clé maîtresse](#8-rotation-de-la-clé-maîtresse)
9. [Tests](#9-tests)
10. [Commandes utiles](#10-commandes-utiles)
11. [Dépannage](#11-dépannage)

---

## 1. Les trois branches

| Branche | Contenu | Base de données |
| --- | --- | --- |
| `main` | Le socle : Docker (PostgreSQL, Mailpit, pgAdmin), configuration, squelette FastAPI et Next.js. Aucune fonctionnalité métier. | `orienta` (vide) |
| `chatbot-without-encryption` | L'application complète : inscription par e-mail avec code, connexion, trois espaces selon le rôle, chatbot RodiumAI, liste de rappel, administration. **Les données personnelles sont stockées en clair.** | `orienta` |
| `chatbot-with-encryption` | La même application, avec le chiffrement : AES-256-GCM, une clé (DEK) par utilisateur protégée par une clé maîtresse (KEK), index aveugle, interrupteur `ENCRYPTION_ENABLED` dans le `.env` et rotation de la KEK en ligne de commande. | `orienta_encrypted` |

Chaque branche part de la précédente. Pour voir exactement ce qu'ajoute le chiffrement :

```bash
git diff chatbot-without-encryption chatbot-with-encryption -- api/
```

Les spécifications techniques sont dans `docs/orienta-backend-tdr.md`, et les schémas des tables dans `docs/orienta-backend-data-model.md`.

Les deux branches chatbot utilisent deux bases différentes, ce qui permet de les comparer côte à côte dans pgAdmin.

## 2. Structure du dépôt

```
orienta/
├── docs/                     # TDR backend et modèle de données (schémas Mermaid)
├── docker-compose.yml        # PostgreSQL, Mailpit, pgAdmin
├── .env.example              # variables de Docker Compose
├── docker/
│   ├── postgres/init/        # crée la base orienta_encrypted au premier démarrage
│   └── pgadmin/servers.json  # serveur PostgreSQL déjà déclaré dans pgAdmin
├── api/                      # backend FastAPI (Python, environnement virtuel)
│   ├── app/
│   │   ├── main.py           # point d'entrée
│   │   ├── config.py         # variables d'environnement
│   │   ├── models.py         # tables SQLAlchemy
│   │   ├── repository.py     # lecture / écriture des données personnelles (en clair ou chiffrées selon la branche)
│   │   ├── crypto/           # chiffrement (branche chatbot-with-encryption)
│   │   ├── llm.py            # adaptateur RodiumAI + modèle factice
│   │   ├── prompts/          # prompt système du chatbot
│   │   ├── modules/          # auth, conversations, agent, admin, demo, health
│   │   └── cli.py            # commandes : create-admin, generate-keys…
│   ├── alembic/              # migrations de la base
│   └── tests/
└── web/                      # frontend Next.js
    ├── app/                  # pages : /, /login, /register, /verify, /patient, /oriagent, /oriadmin
    ├── components/
    └── lib/
```

| Espace | URL | Rôle |
| --- | --- | --- |
| Patient | `/patient` | `PATIENT` (inscription libre) |
| Agent de santé | `/oriagent` | `HEALTH_AGENT` (invité par un administrateur) |
| Administrateur | `/oriadmin` (vue d'ensemble, utilisateurs, agents, orientations, journal) | `ADMIN` (le premier est créé en ligne de commande) |

Tous les profils se connectent sur la même page `/login`. Après connexion, l'API renvoie le rôle et l'application redirige vers le bon espace. L'API revérifie le rôle sur chaque route.

## 3. Prérequis

| Outil | Version | Vérifier |
| --- | --- | --- |
| Git | récent | `git --version` |
| Docker + Docker Compose | Docker 24 ou plus | `docker compose version` |
| Python | 3.12 | `python3 --version` |
| Node.js | 20 LTS ou plus | `node --version` |
| Clé API RodiumAI | — | sur rodiumai.io (facultative : voir `LLM_PROVIDER=fake`) |

Sous Ubuntu, il faut aussi le module des environnements virtuels : `sudo apt install python3.12-venv`.

## 4. Installation de A à Z

Les commandes ci-dessous partent du dossier qui contient le dépôt, par exemple `/home/jeanpierre/Encryption`.

### 4.1 Récupérer le projet

```bash
cd /home/jeanpierre/Encryption
# depuis l'archive :
unzip ~/Téléchargements/orienta.zip
# ou depuis GitHub :
# git clone <url-du-depot> orienta

cd orienta
git branch -a                          # main, chatbot-without-encryption, chatbot-with-encryption
git checkout chatbot-without-encryption
```

### 4.2 Lancer l'infrastructure (Docker)

```bash
cp .env.example .env                   # identifiants locaux, à adapter si besoin
docker compose up -d
docker compose ps                      # postgres doit être "healthy"
```

| Service | Adresse | Identifiants |
| --- | --- | --- |
| PostgreSQL | `localhost:5432` | utilisateur `orienta`, mot de passe `orienta` |
| Mailpit (boîte mail locale) | http://localhost:8025 | aucun |
| pgAdmin | http://localhost:5050 | `admin@orienta.local` / `orienta` |

Dans pgAdmin, le serveur **Orienta (local)** est déjà déclaré. Au premier clic, il demande le mot de passe PostgreSQL : `orienta`.

Le script `docker/postgres/init/01-create-databases.sql` crée la base `orienta_encrypted`. Il ne s'exécute qu'à la création du volume. Si vous aviez déjà lancé PostgreSQL avant, voir [Dépannage](#11-dépannage).

### 4.3 Lancer le backend (environnement virtuel Python)

Dans un premier terminal :

```bash
cd api
python3 -m venv .venv
source .venv/bin/activate              # Windows : .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements-dev.txt

cp .env.example .env
```

Ouvrez `api/.env` et complétez :

1. **Les secrets.** Générez-les avec `python -c "import secrets; print(secrets.token_urlsafe(48))"`, une fois pour `JWT_SECRET`, une fois pour `CODE_HMAC_KEY`. Sur la branche `chatbot-with-encryption`, une seule commande génère tout : `python -m app.cli generate-keys`.
2. **Le modèle d'IA.** Mettez votre clé dans `RODIUMAI_API_KEY` et le modèle dans `RODIUMAI_MODEL` (par défaut `openai/gpt-4o`). Sans clé, mettez `LLM_PROVIDER=fake` : l'assistant répond alors avec des réponses préparées, ce qui est pratique pour répéter la démo hors ligne.
3. **La base.** `DATABASE_URL` pointe vers `orienta` sur les branches `main` et `chatbot-without-encryption`, et vers `orienta_encrypted` sur `chatbot-with-encryption`.

Puis :

```bash
alembic upgrade head                   # crée les tables
python -m app.cli create-admin --email admin@orienta.local --name "Admin Orienta"
                                       # le mot de passe est demandé (10 caractères minimum)
uvicorn app.main:app --reload --port 8000
```

- Santé de l'API : http://localhost:8000/api/v1/health/ready
- Documentation interactive : http://localhost:8000/docs

### 4.4 Lancer le frontend (Next.js)

Dans un second terminal :

```bash
cd web
cp .env.example .env.local             # API_URL=http://localhost:8000
npm install
npm run dev
```

Ouvrez http://localhost:3000. Le navigateur ne parle qu'à Next.js : les appels `/api/*` sont transmis à FastAPI (voir `web/next.config.mjs`). Les cookies de session restent ainsi sur la même origine.

## 5. Premier parcours complet

1. **Patient.** Sur http://localhost:3000/register, créez un compte. Le code à 6 chiffres arrive dans Mailpit (http://localhost:8025). Saisissez-le : vous arrivez sur `/patient`.
2. **Conversation.** Décrivez un symptôme (« J'ai de la fièvre depuis hier »), répondez aux questions. Pour déclencher une urgence, signalez une difficulté à respirer.
3. **Administrateur.** Connectez-vous sur `/login` avec le compte créé par `create-admin` : vous arrivez sur `/oriadmin`. Invitez un agent de santé.
4. **Agent de santé.** Le code d'activation arrive dans Mailpit, avec un lien vers `/accept-invitation`. L'agent choisit son mot de passe et arrive sur `/oriagent`. Il prend le rappel, lit la conversation et le clôt.
5. **Audit.** Dans `/oriadmin`, le journal montre la lecture de la conversation par l'agent.

## 6. Changer de branche

Chaque branche chatbot a sa propre base. Le fichier `api/.env` n'est pas versionné : il reste le même quand vous changez de branche, et c'est à vous d'adapter `DATABASE_URL`.

```bash
# arrêtez uvicorn (Ctrl+C), puis :
git checkout chatbot-with-encryption
cd api
source .venv/bin/activate
pip install -r requirements-dev.txt    # la branche chiffrée ajoute "cryptography"
python -m app.cli generate-keys        # à coller dans api/.env (KEK_V1, BLIND_INDEX_KEY…)
# dans api/.env : DATABASE_URL=...localhost:5432/orienta_encrypted
alembic upgrade head
python -m app.cli create-admin --email admin@orienta.local --name "Admin Orienta"
uvicorn app.main:app --reload --port 8000
```

Le frontend n'a rien à reconfigurer. Relancez `npm run dev` si les pages ont changé.

## 7. Faire la démonstration avant / après

**Avec les deux branches**

1. Sur `chatbot-without-encryption`, créez un patient et une conversation.
2. Dans pgAdmin, ouvrez la base `orienta` et lancez `SELECT * FROM messages;` puis `SELECT * FROM users;` : symptômes, noms et e-mails sont lisibles.
3. Passez sur `chatbot-with-encryption` (section 6) et refaites le même parcours.
4. Dans pgAdmin, base `orienta_encrypted`, mêmes requêtes : il ne reste que des octets illisibles (`content_ciphertext`, `content_nonce`, `email_ciphertext`, `email_blind_index`…). Le patient, lui, relit son historique normalement.

**Avec l'interrupteur (branche `chatbot-with-encryption`)**

Dans `api/.env`, la variable `ENCRYPTION_ENABLED` décide comment les **nouveaux** messages sont enregistrés :

1. Mettez `ENCRYPTION_ENABLED=false`, redémarrez l'API et envoyez un message : dans pgAdmin, il apparaît en clair dans la colonne `content_plaintext`.
2. Remettez `ENCRYPTION_ENABLED=true`, redémarrez et envoyez un autre message : il n'apparaît que sous forme d'octets dans `content_ciphertext`.
3. Le patient relit les deux messages normalement.

Les noms, e-mails et téléphones restent chiffrés dans les deux cas. `ENCRYPTION_ENABLED=false` ne doit jamais être utilisé avec de vraies données.

## 8. Rotation de la clé maîtresse

Branche `chatbot-with-encryption` uniquement. La rotation se fait **sur le serveur, en ligne de commande** : aucune page web ne touche aux clés.

1. Générez une nouvelle clé : `python -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"`.
2. Ajoutez-la dans `api/.env` sous `KEK_V2=...`, **sans supprimer** `KEK_V1`, puis redémarrez l'API.
3. Lancez `python -m app.cli rotate-kek` : toutes les DEK sont rechiffrées avec la KEK v2. Les messages ne sont pas touchés.
4. Vérifiez avec `python -m app.cli keys-status`. Quand la v1 ne protège plus aucune DEK, vous pouvez retirer `KEK_V1` de l'environnement.

## 9. Tests

Les tests utilisent une base dédiée, `orienta_test`, et le modèle factice (aucun appel à RodiumAI).

```bash
docker compose exec postgres createdb -U orienta orienta_test   # une seule fois
cd api
source .venv/bin/activate
pytest -q
```

## 10. Commandes utiles

| Commande (dans `api/`, environnement virtuel actif) | Effet |
| --- | --- |
| `python -m app.cli create-admin --email … --name …` | Crée un administrateur actif |
| `python -m app.cli generate-keys` | Affiche de nouveaux secrets (branche chiffrée) |
| `python -m app.cli keys-status` | Versions de KEK et nombre de DEK protégées (branche chiffrée) |
| `python -m app.cli rotate-kek` | Rotation de la clé maîtresse (branche chiffrée) |
| `python -m app.cli mark-abandoned` | Passe en `ABANDONED` les conversations sans activité depuis 24 h |
| `python -m app.cli purge-expired` | Supprime les codes et sessions expirés |
| `alembic upgrade head` / `alembic downgrade -1` | Applique / annule une migration |

| Commande (à la racine) | Effet |
| --- | --- |
| `docker compose up -d` / `docker compose down` | Démarre / arrête l'infrastructure |
| `docker compose logs -f mailpit` | Suit les journaux d'un service |
| `docker compose down -v` | Arrête tout **et efface les données** (bases et pgAdmin) |

## 11. Dépannage

| Problème | Solution |
| --- | --- |
| `port is already allocated` sur 5432 | Un PostgreSQL tourne déjà sur la machine. Changez `POSTGRES_PORT=5433` dans `.env` et le port dans `DATABASE_URL`. |
| La base `orienta_encrypted` n'existe pas | Le volume existait déjà avant le script d'initialisation. Créez-la : `docker compose exec postgres createdb -U orienta orienta_encrypted`. |
| Aucun e-mail dans Mailpit | Vérifiez `SMTP_HOST=localhost` et `SMTP_PORT=1025` dans `api/.env`, et que le conteneur `mailpit` tourne. |
| `LLM_UNAVAILABLE` dans le chat | Clé `RODIUMAI_API_KEY` absente ou invalide, solde insuffisant ou modèle inconnu. Pour répéter hors ligne : `LLM_PROVIDER=fake`. |
| `KEK_NOT_CONFIGURED` ou `KEK_NOT_LOADED` | `KEK_V1` manque dans `api/.env`, ou la migration `0002` n'a pas été appliquée sur `orienta_encrypted`. |
| `Migration 0002 needs an empty database` | Vous lancez la branche chiffrée sur la base `orienta`. Pointez `DATABASE_URL` vers `orienta_encrypted`. |
| Redirection en boucle vers `/login` | L'API ne tourne pas, ou `API_URL` dans `web/.env.local` ne pointe pas vers elle. |

---

**Sécurité.** Ne versionnez jamais `api/.env` ni `web/.env.local` (ils sont dans `.gitignore`). En production : `APP_ENV=production`, `COOKIE_SECURE=true`, `ENCRYPTION_ENABLED=true`, HTTPS obligatoire et une clé maîtresse dans un coffre à secrets plutôt que dans un fichier.
