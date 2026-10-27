# Orienta — Spécifications techniques du backend (TDR)

> Version 0.2 · 27 octobre 2026 · Périmètre : backend de la première version (date de lancement à trancher, voir §15).
> Document de référence pour le développement de l'API. Il découle du cahier des charges (fonctionnalités F1 à F12), complété par les décisions du 27 octobre 2026 (F1 modifiée, F13 à F15 ajoutées). Les évolutions M1 et M2 sont hors périmètre, mais l'architecture doit permettre de les ajouter sans refonte.

Décisions du 27 octobre 2026, à reporter dans le cahier des charges :

| # | Décision |
| --- | --- |
| F1 (modifiée) | L'inscription se fait par adresse e-mail et mot de passe, et non plus par téléphone. |
| F13 (nouvelle) | L'adresse e-mail est vérifiée par un code envoyé par e-mail avant toute utilisation du compte. |
| F14 (nouvelle) | Les trois profils utilisent la même application. Après connexion, le rôle est vérifié et l'utilisateur est redirigé vers son espace dédié. |
| F15 (nouvelle, proposée) | L'administrateur crée et désactive les comptes des agents de santé et des autres administrateurs. |
| F9 (retirée) | Pas de pseudonymisation dans le projet : le message est envoyé tel quel au modèle d'IA. |
| Organisation | Un seul dépôt `orienta` avec `api/` et `web/`, et trois branches : `main` (socle), `chatbot-without-encryption`, `chatbot-with-encryption`. |
| Infrastructure locale | Docker pour PostgreSQL, Mailpit (e-mails) et pgAdmin ; backend dans un environnement virtuel Python. |
| Modèle d'IA | RodiumAI, via le SDK Python `rodiumai`. |
| Espaces frontend | `/patient`, `/oriagent` (agents de santé), `/oriadmin` (administrateurs). |

---

## 1. Périmètre du backend

Le backend FastAPI est la source de vérité : il porte toute la logique métier, tout le chiffrement et toutes les règles d'accès. Un seul client le consomme : l'application web Next.js, qui sert les trois espaces (patient, agent de santé, administrateur).

| Domaine | Fonctionnalités CDC couvertes |
| --- | --- |
| Comptes et authentification | F1, F2, F13, F14 |
| Conversation et pré-orientation | F3, F4, F5 |
| Chiffrement et gestion des clés | F6, F12 |
| Espace agent de santé | F10, F11 |
| Administration (API admin) | F15, F12 |
| Module de démonstration | F7, F8 |
| Qualité, déploiement | Toutes |

Hors périmètre de cette version : M1 (coffre à secrets Vault ou KMS à la place du fichier `.env`) et M2 (annuaire des centres de santé pour orienter vers le plus proche). Voir §14 « Préparation des évolutions ».

Le module de démonstration (F7, F8) n'existe que dans la branche `chatbot-with-encryption` et n'est actif que si `DEMO_MODE=true`. Il ne doit jamais être activé sur un environnement qui contient de vraies données.

---

## 2. Stack technique

| Élément | Choix | Remarque |
| --- | --- | --- |
| Runtime | Python 3.12 | Version figée dans l'image Docker |
| Framework | FastAPI | Monolithe modulaire |
| Serveur ASGI | Uvicorn | Derrière un reverse proxy (Caddy) qui termine le TLS |
| Base de données | PostgreSQL 16 | |
| ORM | SQLAlchemy 2.0 (async) + Alembic | Alembic pour toutes les migrations |
| Cache, files de tâches | Aucun en v1 | Pas de Redis : rien à protéger hors de PostgreSQL ; tâches planifiées lancées par commande (§10) |
| Validation | Pydantic v2 | `extra="forbid"` : rejet des champs inconnus |
| Authentification | JWT HS256 (PyJWT), Argon2id (argon2-cffi) | Jetons dans des cookies httpOnly |
| Chiffrement | `cryptography` (AESGCM), `hmac` + `hashlib` (bibliothèque standard) | Branche `chatbot-with-encryption` ; aucun algorithme implémenté à la main |
| Modèle d'IA | RodiumAI, SDK `rodiumai` ; modèle `openai/gpt-4o` par défaut (`RODIUMAI_MODEL`) | Passerelle cloud : les messages sortent du serveur (voir §11) ; `LLM_PROVIDER=fake` pour les tests et les répétitions |
| E-mails | SMTP ; Mailpit en local, fournisseur de production à trancher (§15) | Modèles traduits (français au lancement) |
| Outils locaux | Docker Compose : PostgreSQL 16, Mailpit, pgAdmin 4 | L'API et le frontend tournent sur la machine hôte |
| Notifications push | Non applicable | |
| Paiement | Non applicable | |
| Documentation API | OpenAPI généré par FastAPI | `/docs` désactivé en production |
| Logs, santé | `logging` standard, routes `/health/*` | Corps des requêtes, prompts et réponses jamais journalisés |
| Tests | pytest, httpx `AsyncClient`, testcontainers | |
| Frontend (pour mémoire) | Next.js 15 | Dossier `web/` ; hors de ce document |

---

## 3. Architecture

### 3.1 Principes

- Monolithe modulaire : une seule équipe, un seul déploiement, des frontières de modules nettes pour pouvoir découper plus tard.
- Un seul processus `api` (HTTP, sans état). Les tâches planifiées sont des commandes (`python -m app.cli …`) lancées par cron ou à la main.
- Couches par module : `router` → `service` → `repository` ; intégrations externes via des adaptateurs dans `infrastructure/`.
- Toute lecture ou écriture d'une donnée personnelle passe par `app/repository.py`. C'est le seul fichier (avec les modèles) qui diffère entre les deux branches chatbot : en clair dans l'une, chiffré dans l'autre.
- Transitions critiques atomiques : transaction + mise à jour conditionnelle (`WHERE status = ...`).
- Les e-mails contenant un code sont envoyés dans le processus `api` (tâche d'arrière-plan FastAPI), après la réponse ; le code n'est jamais stocké en clair ni journalisé.

### 3.2 Dépôt et branches

Un seul dépôt Git, `orienta`, contient le backend (`api/`) et le frontend (`web/`). Il a exactement trois branches, chacune construite sur la précédente :

| Branche | Contenu | Base locale |
| --- | --- | --- |
| `main` | Socle : Docker Compose, configuration, squelette FastAPI (santé, format d'erreur, Alembic) et squelette Next.js, README | `orienta` |
| `chatbot-without-encryption` | Toutes les fonctionnalités du périmètre, données personnelles en clair (migration `0001`) | `orienta` |
| `chatbot-with-encryption` | Même code + chiffrement (§8), module de démonstration (F7, F8) et rotation de la KEK (migration `0002`) | `orienta_encrypted` |

Les deux branches chatbot utilisent deux bases distinctes, créées par Docker, pour pouvoir les comparer côte à côte dans pgAdmin.

```
orienta/
├── docker-compose.yml          # postgres, mailpit, pgadmin
├── docker/
│   ├── postgres/init/          # creates the orienta_encrypted database
│   └── pgadmin/servers.json    # preconfigured server
├── api/
│   ├── app/
│   │   ├── main.py             # entry point of the api process
│   │   ├── cli.py              # create-admin, generate-keys, mark-abandoned, purge-expired
│   │   ├── config.py           # environment settings (pydantic-settings)
│   │   ├── db.py               # engine, session, declarative base
│   │   ├── errors.py           # unique error format, request id
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── repository.py       # every read and write of personal data (plain or encrypted)
│   │   ├── security.py         # password hashing, tokens, verification codes
│   │   ├── deps.py             # current user, role guards
│   │   ├── audit.py            # append-only audit log
│   │   ├── mail.py             # smtp sender and translated templates
│   │   ├── llm.py              # RodiumAI adapter and fake model
│   │   ├── prompts/            # system prompt of the triage assistant
│   │   ├── crypto/             # envelope encryption, keyring, blind index (encrypted branch)
│   │   └── modules/
│   │       ├── auth/           # register, codes, login, refresh, logout, me
│   │       ├── conversations/  # patient chat and triage
│   │       ├── agent/          # urgent callback list for health agents
│   │       ├── admin/          # users, audit log, keys
│   │       ├── demo/           # encryption toggle and raw database view (encrypted branch)
│   │       └── health/         # liveness and readiness probes
│   ├── alembic/                # migrations
│   └── tests/
└── web/                        # Next.js app: /patient, /oriagent, /oriadmin
```

### 3.3 Conventions

| Sujet | Règle |
| --- | --- |
| Préfixe | `/api/v1` ; espace agent sous `/api/v1/agent` ; API admin sous `/api/v1/admin` ; démo sous `/api/v1/demo`. Les pages frontend correspondantes sont `/patient`, `/oriagent` et `/oriadmin` |
| Identifiants | UUID v4 générés par l'application |
| Montants | Non applicable |
| Dates | Stockées en UTC (`timestamptz`) ; affichées dans le fuseau du navigateur (Bénin UTC+1, Togo UTC+0) |
| Unités | Durées en secondes dans la configuration et les réglages |
| Pagination | Par curseur (`cursor`, `limit` ≤ 50) |
| Données chiffrées | Chaque champ chiffré = deux colonnes : `<field>_ciphertext` (`bytea`, texte chiffré + tag de 16 octets) et `<field>_nonce` (`bytea`, 12 octets) |
| Langue technique | Tout en anglais : tables, colonnes, énumérations, statuts, codes et messages d'erreur, logs, documentation API |
| Textes utilisateurs | Modèles traduits (français au lancement), jamais en dur dans le code ; l'avertissement « ne remplace pas un soignant » est un modèle affiché par le frontend, pas une sortie du modèle d'IA |
| Suppression | Pas de suppression de compte en v1 (voir §15) ; méthode retenue si elle est ajoutée : destruction de la DEK de l'utilisateur (crypto-shredding) |
| Nommage | Tables et colonnes en `snake_case`, modèles SQLAlchemy en `PascalCase` |

Format d'erreur unique :

```json
{
  "error": {
    "code": "VERIFICATION_CODE_INVALID",
    "message": "The verification code is invalid.",
    "details": {},
    "requestId": "01J9Z3K8QY4M2N7P5R6S8T0V1W"
  }
}
```

Codes d'erreur métier :

| HTTP | Code | Cas |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | Corps de requête invalide |
| 401 | `INVALID_CREDENTIALS` | E-mail ou mot de passe incorrect (message identique dans les deux cas) |
| 401 | `UNAUTHENTICATED` | Pas de jeton, jeton invalide ou session révoquée |
| 401 | `TOKEN_EXPIRED` | Jeton d'accès expiré ; le frontend appelle alors `/auth/refresh` |
| 403 | `EMAIL_NOT_VERIFIED` | Connexion avant vérification de l'e-mail |
| 403 | `ACCOUNT_DISABLED` | Compte désactivé par un administrateur |
| 403 | `FORBIDDEN_ROLE` | Route d'un autre espace que celui du rôle |
| 404 | `RESOURCE_NOT_FOUND` | Ressource absente ou appartenant à un autre utilisateur |
| 409 | `EMAIL_ALREADY_REGISTERED` | Invitation d'une adresse qui a déjà un compte |
| 409 | `INVALID_TRANSITION` | Changement de statut non autorisé |
| 409 | `KEK_NOT_PROVISIONED` | Rotation demandée sans nouvelle `KEK_V<n>` chargée |
| 409 | `CONVERSATION_CLOSED` | Message envoyé dans une conversation terminée |
| 409 | `CALLBACK_ALREADY_ASSIGNED` | Rappel déjà pris par un autre agent |
| 422 | `VERIFICATION_CODE_INVALID` | Code erroné |
| 422 | `VERIFICATION_CODE_EXPIRED` | Code expiré |
| 423 | `ACCOUNT_LOCKED` | Trop d'échecs de connexion ou de code |
| 429 | `RATE_LIMITED` | Limite de débit atteinte, y compris le délai entre deux envois de code |
| 503 | `LLM_UNAVAILABLE` | Le modèle d'IA ne répond pas ou renvoie une sortie invalide |

---

## 4. Authentification et autorisations

### 4.1 Types de comptes

Une seule table `users`, un seul formulaire de connexion. Le rôle détermine l'espace.

| Compte | Rôle (`user_role`) | Création | Connexion | Espace frontend |
| --- | --- | --- | --- | --- |
| Patient | `PATIENT` | Inscription libre (F1) | E-mail + mot de passe | `/patient` |
| Agent de santé | `HEALTH_AGENT` | Invitation par un administrateur (F15) | E-mail + mot de passe | `/oriagent` |
| Administrateur | `ADMIN` | Invitation par un administrateur ; le premier par la commande `python -m app.cli create-admin` | E-mail + mot de passe | `/oriadmin` |

Jeton : JWT signé en HS256 avec `JWT_SECRET`. Claims : `sub` (id utilisateur), `role`, `exp`, `iat`, `jti`.

### 4.2 Parcours d'inscription et de vérification (F1, F13)

1. Le patient envoie son e-mail, son mot de passe, son nom complet, son téléphone (facultatif, voir §15) et la version du consentement acceptée (`POST /auth/register`).
2. Le serveur calcule l'index aveugle de l'e-mail. S'il existe déjà, il répond `202` comme pour une nouvelle inscription et envoie à cette adresse un e-mail « vous avez déjà un compte » : la route ne révèle pas quelles adresses sont inscrites.
3. Sinon, dans une seule transaction : création de l'utilisateur (`PENDING_VERIFICATION`), génération de sa DEK, chiffrement de l'e-mail, du nom et du téléphone, enregistrement du consentement, création d'un code de vérification.
4. Le code (6 chiffres, généré avec `secrets`) est envoyé par e-mail. Seule son empreinte HMAC-SHA256 est stockée. Validité : 10 minutes (proposé).
5. Le patient saisit le code (`POST /auth/verify-email`). Après 5 essais faux (proposé), le code est invalidé ; il faut en demander un nouveau.
6. Code valide : statut `ACTIVE`, `email_verified_at` renseigné, cookies de session posés, réponse avec le rôle.
7. Renvoi d'un code (`POST /auth/resend-code`) : au plus un toutes les 60 secondes et 5 par heure (proposé). Chaque nouveau code invalide le précédent.

Les comptes agent et administrateur suivent le même mécanisme, avec un code d'objet `INVITATION` : l'invité saisit le code et choisit son mot de passe (`POST /auth/accept-invitation`).

### 4.3 Connexion et redirection selon le rôle (F2, F14)

1. `POST /auth/login` avec e-mail et mot de passe.
2. Le serveur retrouve l'utilisateur par l'index aveugle de l'e-mail, vérifie le hachage Argon2id, puis le statut et `locked_until`.
3. Réponse `200` : `{ "user": { "id", "role", "status" } }` et deux cookies (`access_token`, `refresh_token`).
4. Le frontend redirige selon `role` : `PATIENT` → `/patient`, `HEALTH_AGENT` → `/oriagent`, `ADMIN` → `/oriadmin`.
5. Chaque espace appelle `GET /auth/me` au chargement ; si le rôle ne correspond pas, il redirige vers l'espace du rôle, et vers `/login` sans session. Ce contrôle sert l'ergonomie ; le contrôle qui fait foi est celui du backend (§4.5).

Le navigateur ne parle qu'à l'origine Next.js : les appels `/api/*` sont transmis à FastAPI par une réécriture (`web/next.config.mjs`). Les cookies httpOnly restent donc sur une seule origine, sans CORS.

### 4.4 Sessions

- Jeton d'accès : 15 minutes (proposé), cookie `access_token`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` en production (`COOKIE_SECURE=true`).
- Jeton de rafraîchissement : 7 jours (proposé), cookie `refresh_token` limité à `Path=/api/v1/auth`, stocké haché (SHA-256), rotation à chaque usage. La réutilisation d'un jeton déjà remplacé révoque toute sa famille.
- Déconnexion : révocation du jeton de rafraîchissement et suppression des cookies.
- Désactivation d'un compte : révocation immédiate de tous ses jetons de rafraîchissement.
- Blocage : 5 échecs de connexion → verrouillage 15 minutes (`locked_until`) (proposé).
- Mots de passe : 10 caractères minimum (proposé), hachage Argon2id avec les paramètres par défaut de `argon2-cffi`.

### 4.5 Autorisations

- Une dépendance FastAPI `require_role(...)` protège chaque groupe de routes : routes patient → `PATIENT` ; `/agent/*` → `HEALTH_AGENT` ; `/admin/*` et `/demo/*` → `ADMIN`. Un mauvais rôle renvoie `403 FORBIDDEN_ROLE`.
- Patient : contrôle de propriété sur chaque ressource (`conversations.patient_id = sub`). Une ressource d'un autre patient renvoie `404`, pas `403`.
- Agent de santé : il ne lit une conversation que si un rappel de cette conversation lui est attribué (F11). Chaque lecture est journalisée.
- Administrateur : il gère les comptes, les réglages et les clés, mais n'a aucune route qui déchiffre une conversation.
- Pas de permissions fines `resource.action` en v1 : trois rôles fixes suffisent (proposé).

### 4.6 Statuts de compte

```mermaid
stateDiagram-v2
    [*] --> PENDING_VERIFICATION : patient registers / admin invites
    PENDING_VERIFICATION --> ACTIVE : valid code (email verified or invitation accepted)
    ACTIVE --> DISABLED : admin disables
    DISABLED --> ACTIVE : admin re-enables
```

| Status | Meaning |
| --- | --- |
| `PENDING_VERIFICATION` | Account created, email not verified yet; login refused |
| `ACTIVE` | Email verified; the user can sign in |
| `DISABLED` | Disabled by an admin; all sessions revoked |

Le verrouillage temporaire n'est pas un statut : il est porté par `locked_until`. Un administrateur ne peut pas désactiver son propre compte ni le dernier administrateur actif.

---

## 5. Modèle de données

### 5.1 Vue d'ensemble

Les schémas des relations entre tables, découpés par domaine, sont dans le fichier séparé `orienta-backend-data-model.md`.

### 5.2 Énumérations

| Énumération | Valeurs |
| --- | --- |
| `user_role` | `PATIENT`, `HEALTH_AGENT`, `ADMIN` |
| `user_status` | `PENDING_VERIFICATION`, `ACTIVE`, `DISABLED` |
| `verification_purpose` | `EMAIL_VERIFICATION`, `INVITATION` |
| `user_key_status` | `ACTIVE`, `DESTROYED` |
| `kek_status` | `ACTIVE`, `RETIRED` |
| `conversation_status` | `IN_PROGRESS`, `ORIENTED`, `ABANDONED` |
| `orientation_level` | `EMERGENCY`, `CONSULTATION_48H`, `HOME_CARE` |
| `message_sender` | `PATIENT`, `ASSISTANT` |
| `encryption_mode` | `ENCRYPTED`, `PLAINTEXT` |
| `callback_status` | `PENDING`, `ASSIGNED`, `COMPLETED`, `UNREACHABLE` |

Statut de la conversation, objet métier principal :

| Status | Meaning | Étape CDC |
| --- | --- | --- |
| `IN_PROGRESS` | The patient is describing symptoms or answering follow-up questions | F3 |
| `ORIENTED` | The assistant gave one of the three orientation levels | F4 |
| `ABANDONED` | No patient message for 24 hours before orientation (proposé) | F3 |

### 5.3 Tables

Les colonnes ci-dessous sont celles de la branche `chatbot-with-encryption`. Dans `chatbot-without-encryption`, chaque paire `<field>_ciphertext` / `<field>_nonce` est remplacée par une colonne en clair (`users.email` unique, `users.full_name`, `users.phone`, `messages.content`, `callback_requests.outcome_note`), sans index aveugle, sans `messages.encryption_mode` et sans les tables `user_keys` et `key_encryption_keys`.

Colonnes communes (non répétées) : `id` PK `uuid`, `created_at`, `updated_at`. Les tables de journal sont en ajout seul (pas de `updated_at`) : `consents`, `messages`, `audit_logs`.

#### Comptes et authentification

**`users`** — tous les comptes, quel que soit le rôle

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `role` | `user_role` | NOT NULL, INDEX |
| `status` | `user_status` | NOT NULL, défaut `PENDING_VERIFICATION` |
| `email_ciphertext` | `bytea` | NOT NULL ; chiffré avec la DEK de l'utilisateur |
| `email_nonce` | `bytea` | NOT NULL, 12 octets |
| `email_blind_index` | `bytea` | NOT NULL, UNIQUE ; HMAC-SHA256 de l'e-mail normalisé (minuscules, sans espaces) |
| `full_name_ciphertext` | `bytea` | NOT NULL |
| `full_name_nonce` | `bytea` | NOT NULL |
| `phone_ciphertext` | `bytea` | NULL |
| `phone_nonce` | `bytea` | NULL |
| `phone_blind_index` | `bytea` | NULL ; index unique partiel `WHERE phone_blind_index IS NOT NULL` |
| `password_hash` | `text` | NULL tant qu'un invité n'a pas choisi son mot de passe ; Argon2id |
| `email_verified_at` | `timestamptz` | NULL |
| `failed_login_count` | `int` | NOT NULL, défaut 0 |
| `locked_until` | `timestamptz` | NULL |
| `last_login_at` | `timestamptz` | NULL |
| `invited_by_id` | `uuid` | NULL, FK `users` ; NULL pour un patient et pour le premier administrateur |

Contrainte : `status = 'ACTIVE'` implique `email_verified_at IS NOT NULL` et `password_hash IS NOT NULL`.

**`email_verification_codes`** — codes d'inscription et d'invitation

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `user_id` | `uuid` | NOT NULL, FK `users`, INDEX |
| `purpose` | `verification_purpose` | NOT NULL |
| `code_hash` | `bytea` | NOT NULL ; HMAC-SHA256 du code avec `CODE_HMAC_KEY` |
| `expires_at` | `timestamptz` | NOT NULL |
| `attempt_count` | `int` | NOT NULL, défaut 0 |
| `consumed_at` | `timestamptz` | NULL ; renseigné à l'usage ou à l'invalidation |

Index unique partiel : un seul code non consommé par `(user_id, purpose)` `WHERE consumed_at IS NULL`.

**`refresh_tokens`** — jetons de rafraîchissement

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `user_id` | `uuid` | NOT NULL, FK `users`, INDEX |
| `family_id` | `uuid` | NOT NULL, INDEX ; partagé par toutes les rotations d'une même session |
| `token_hash` | `bytea` | NOT NULL, UNIQUE ; SHA-256 du jeton |
| `expires_at` | `timestamptz` | NOT NULL |
| `revoked_at` | `timestamptz` | NULL |
| `replaced_by_id` | `uuid` | NULL, FK `refresh_tokens`, UNIQUE |

**`consents`** : `user_id` (NOT NULL, FK `users`, INDEX), `consent_version` (`text`, NOT NULL), `accepted_at` (`timestamptz`, NOT NULL). Ajout seul : une nouvelle version du texte crée une nouvelle ligne.

#### Chiffrement et clés

**`key_encryption_keys`** — métadonnées des clés maîtresses ; la clé elle-même n'est jamais en base (variables `KEK_V<version>`)

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `version` | `int` | NOT NULL, UNIQUE |
| `status` | `kek_status` | NOT NULL |
| `activated_at` | `timestamptz` | NOT NULL |
| `retired_at` | `timestamptz` | NULL |

Index unique partiel : une seule ligne `WHERE status = 'ACTIVE'`. La migration `0002` crée la version 1 en `ACTIVE`. La version active est lue en base, pas dans une variable d'environnement.

**`user_keys`** — une DEK par utilisateur, stockée chiffrée par la KEK

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `user_id` | `uuid` | NOT NULL, FK `users`, UNIQUE |
| `kek_id` | `uuid` | NOT NULL, FK `key_encryption_keys`, INDEX |
| `wrapped_dek` | `bytea` | NULL après destruction ; DEK de 32 octets chiffrée par la KEK (48 octets avec le tag) |
| `wrapped_dek_nonce` | `bytea` | NULL après destruction ; 12 octets |
| `status` | `user_key_status` | NOT NULL, défaut `ACTIVE` |
| `destroyed_at` | `timestamptz` | NULL |

Contrainte : `status = 'DESTROYED'` implique `wrapped_dek IS NULL`.

#### Conversations et pré-orientation

**`conversations`** — une demande de pré-orientation d'un patient

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `patient_id` | `uuid` | NOT NULL, FK `users`, INDEX |
| `status` | `conversation_status` | NOT NULL, défaut `IN_PROGRESS` |
| `orientation_level` | `orientation_level` | NULL tant que la conversation n'est pas orientée |
| `oriented_at` | `timestamptz` | NULL |
| `follow_up_count` | `int` | NOT NULL, défaut 0 ; nombre de questions de suivi posées |
| `last_message_at` | `timestamptz` | NOT NULL, INDEX (pour la tâche d'abandon) |

Contrainte : `(status = 'ORIENTED') = (orientation_level IS NOT NULL)`.

**`messages`** — messages du patient et de l'assistant, en ajout seul

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `conversation_id` | `uuid` | NOT NULL, FK `conversations` |
| `sequence` | `int` | NOT NULL ; UNIQUE `(conversation_id, sequence)` |
| `sender` | `message_sender` | NOT NULL |
| `encryption_mode` | `encryption_mode` | NOT NULL, défaut `ENCRYPTED` |
| `content_ciphertext` | `bytea` | NULL ; chiffré avec la DEK du patient |
| `content_nonce` | `bytea` | NULL ; 12 octets |
| `content_plaintext` | `text` | NULL ; rempli uniquement en mode `PLAINTEXT` (démo F7) |

Contrainte : en `ENCRYPTED`, `content_ciphertext` et `content_nonce` NOT NULL et `content_plaintext` NULL ; en `PLAINTEXT`, l'inverse. L'API refuse `PLAINTEXT` si `DEMO_MODE=false`.

#### Espace agent de santé

**`callback_requests`** — rappel d'un patient orienté en urgence (F10)

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `conversation_id` | `uuid` | NOT NULL, FK `conversations`, UNIQUE |
| `status` | `callback_status` | NOT NULL, défaut `PENDING` ; INDEX `(status, created_at)` |
| `assigned_agent_id` | `uuid` | NULL, FK `users`, INDEX |
| `assigned_at` | `timestamptz` | NULL |
| `closed_at` | `timestamptz` | NULL |
| `outcome_note_ciphertext` | `bytea` | NULL ; note de l'agent, chiffrée avec la DEK du patient |
| `outcome_note_nonce` | `bytea` | NULL |

Contrainte : `status IN ('ASSIGNED', 'COMPLETED', 'UNREACHABLE')` implique `assigned_agent_id IS NOT NULL`.

#### Administration et système

**`audit_logs`** — journal d'audit, en ajout seul (F11)

| Colonne | Type | Contraintes / remarques |
| --- | --- | --- |
| `actor_id` | `uuid` | NULL (tâche système) ; pas de FK, pour que le journal survive à toute suppression |
| `actor_role` | `user_role` | NULL |
| `action` | `text` | NOT NULL, INDEX ; ex. `conversation.read`, `user.disabled`, `kek.rotated` |
| `resource_type` | `text` | NOT NULL |
| `resource_id` | `uuid` | NULL, INDEX |
| `ip_hash` | `bytea` | NULL ; HMAC de l'adresse IP |
| `metadata` | `jsonb` | NOT NULL, défaut `{}` ; jamais de donnée personnelle ni de contenu |

Les paramètres réglables (durée des codes, seuils de verrouillage, nombre maximal de questions de suivi, délai d'abandon) sont des variables d'environnement en v1 (§12), sans table `settings`.

--- | --- |
| `verification.code_ttl_seconds` | 600 |
| `verification.max_attempts` | 5 |
| `verification.resend_cooldown_seconds` | 60 |
| `verification.max_resends_per_hour` | 5 |
| `auth.max_failed_logins` | 5 |
| `auth.lock_duration_seconds` | 900 |
| `triage.max_follow_up_questions` | 4 |
| `conversations.abandon_after_seconds` | 86400 |

---

## 6. Cycles de vie

### 6.1 Conversation : transitions autorisées

| De | Vers | Déclencheur | Conditions |
| --- | --- | --- | --- |
| — | `IN_PROGRESS` | Patient : `POST /conversations` avec un premier message | Compte `ACTIVE` |
| `IN_PROGRESS` | `ORIENTED` | Système : le modèle renvoie la décision `ORIENT` (§7) | Niveau d'orientation valide |
| `IN_PROGRESS` | `ABANDONED` | Commande `python -m app.cli mark-abandoned` | Aucun message depuis `CONVERSATIONS_ABANDON_AFTER_SECONDS` |

Toute autre transition renvoie `409 INVALID_TRANSITION`. Un message dans une conversation `ORIENTED` ou `ABANDONED` renvoie `409 CONVERSATION_CLOSED`. Chaque transition : transaction conditionnelle et ligne dans `audit_logs`.

### 6.2 Conversation : diagramme des statuts

```mermaid
stateDiagram-v2
    [*] --> IN_PROGRESS : patient sends first message
    IN_PROGRESS --> ORIENTED : model decision ORIENT
    IN_PROGRESS --> ABANDONED : no message for 24 h
    ORIENTED --> [*]
    ABANDONED --> [*]
```

Une conversation passée en `ORIENTED` avec le niveau `EMERGENCY` crée, dans la même transaction, un `callback_requests` en `PENDING`.

### 6.3 Rappel d'urgence : transitions autorisées (F10)

| De | Vers | Déclencheur | Conditions |
| --- | --- | --- | --- |
| — | `PENDING` | Système : conversation orientée `EMERGENCY` | |
| `PENDING` | `ASSIGNED` | Agent : prend le rappel | `WHERE status = 'PENDING'` ; sinon `409 CALLBACK_ALREADY_ASSIGNED` |
| `ASSIGNED` | `PENDING` | Agent : relâche le rappel | Seul l'agent attribué |
| `ASSIGNED` | `COMPLETED` | Agent : patient joint | Seul l'agent attribué ; note facultative |
| `ASSIGNED` | `UNREACHABLE` | Agent : patient injoignable | Seul l'agent attribué ; note facultative |

```mermaid
stateDiagram-v2
    [*] --> PENDING : conversation oriented EMERGENCY
    PENDING --> ASSIGNED : agent claims
    ASSIGNED --> PENDING : agent releases
    ASSIGNED --> COMPLETED : patient reached
    ASSIGNED --> UNREACHABLE : patient not reached
    COMPLETED --> [*]
    UNREACHABLE --> [*]
```

| Status | Meaning |
| --- | --- |
| `PENDING` | Waiting for an agent |
| `ASSIGNED` | An agent is handling the callback |
| `COMPLETED` | The patient was reached |
| `UNREACHABLE` | The agent could not reach the patient |

### 6.4 Clés : statuts

`user_keys` :

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : user created
    ACTIVE --> DESTROYED : crypto-shredding (not exposed in v1)
```

`key_encryption_keys` :

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : rotation activates the new version
    ACTIVE --> RETIRED : next rotation
```

| Table | Status | Meaning |
| --- | --- | --- |
| `user_keys` | `ACTIVE` | The DEK can encrypt and decrypt the user's data |
| `user_keys` | `DESTROYED` | The wrapped DEK is erased; the user's data can never be decrypted again |
| `key_encryption_keys` | `ACTIVE` | The KEK used to wrap new DEKs |
| `key_encryption_keys` | `RETIRED` | Kept loaded only until every DEK is re-wrapped with the active KEK |


---

## 7. Pré-orientation : traitement d'un message (F3, F4)

Déroulé de `POST /conversations/{id}/messages` (et du premier message de `POST /conversations`) :

1. Vérifier le rôle `PATIENT`, la propriété de la conversation et le statut `IN_PROGRESS`. Verrouiller la ligne (`SELECT ... FOR UPDATE`) pour sérialiser deux envois simultanés.
2. Branche chiffrée : charger la DEK du patient et la déchiffrer avec la KEK, en mémoire, pour la durée de la requête (§8).
3. Lire l'historique de la conversation (déchiffré dans la branche chiffrée).
4. Construire les messages envoyés au modèle : prompt système (`app/prompts/triage_system_fr.txt`, en français), historique, nouveau message. Le prompt impose une sortie JSON :
   `{ "reply": string, "decision": "ASK_FOLLOW_UP" | "ORIENT", "orientationLevel": null | "EMERGENCY" | "CONSULTATION_48H" | "HOME_CARE" }`.
5. Appeler RodiumAI (`chat.completions.create`, délai maximal `LLM_TIMEOUT_SECONDS`). Valider la sortie avec Pydantic ; une nouvelle tentative si elle est invalide, puis `503 LLM_UNAVAILABLE`. En cas d'échec, rien n'est enregistré : le patient renvoie son message.
6. Garde-fous serveur :
    - si `follow_up_count` atteint `TRIAGE_MAX_FOLLOW_UP_QUESTIONS`, un second appel impose la décision `ORIENT` ; si le modèle refuse encore, le niveau `CONSULTATION_48H` est appliqué par défaut (proposé, à valider par un soignant) ;
    - les mots-clés de `TRIAGE_RED_FLAG_KEYWORDS`, vérifiés côté serveur, forcent `EMERGENCY` (liste vide par défaut, à faire valider par un soignant, voir §15).
7. Transaction : insertion du message patient et du message assistant (chacun chiffré avec un nouveau nonce dans la branche chiffrée), mise à jour de `follow_up_count` et `last_message_at`, passage à `ORIENTED` si besoin, création du `callback_requests` si `EMERGENCY`.
8. Réponse : la conversation complète, avec son statut et son niveau d'orientation.

| Décision du modèle | Effet |
| --- | --- |
| `ASK_FOLLOW_UP` | `follow_up_count` + 1 ; la conversation reste `IN_PROGRESS` |
| `ORIENT` | Passage à `ORIENTED` avec le niveau renvoyé ; rappel créé si `EMERGENCY` |

Aucune pseudonymisation n'est appliquée : RodiumAI reçoit le texte du patient tel quel. Le chiffrement protège le stockage, pas l'appel au modèle (voir §11).

---

## 8. Chiffrement (F6, F12) — branche `chatbot-with-encryption`

### 8.1 Algorithmes

| Usage | Algorithme | Clé |
| --- | --- | --- |
| Champs sensibles (e-mail, nom, téléphone, messages, notes) | AES-256-GCM, nonce aléatoire de 12 octets à chaque chiffrement | DEK de l'utilisateur concerné ; messages et notes : DEK du patient |
| Protection des DEK | AES-256-GCM | KEK active (`KEK_V<version>`) |
| Recherche par e-mail ou téléphone | HMAC-SHA256 (index aveugle) | `BLIND_INDEX_KEY`, distincte de la KEK |
| Codes de vérification (deux branches) | HMAC-SHA256 | `CODE_HMAC_KEY` |
| Mots de passe (deux branches) | Argon2id | — |
| Jetons de rafraîchissement (deux branches) | SHA-256 d'un jeton aléatoire de 32 octets | — |
| Signature des JWT (deux branches) | HS256 | `JWT_SECRET` |

### 8.2 Données associées (AAD)

Chaque chiffrement AES-GCM lie le texte chiffré à sa place en base. Copier un texte chiffré dans une autre ligne fait échouer le déchiffrement.

| Donnée | AAD |
| --- | --- |
| Champ de `users` | `users:{user_id}:{field}` |
| `messages.content` | `messages:{conversation_id}:{sequence}` |
| `callback_requests.outcome_note` | `callback_requests:{id}:outcome_note` |
| `user_keys.wrapped_dek` | `user_keys:{user_id}:kek:{kek_version}` |

Un échec de déchiffrement est une erreur interne (`500`) journalisée sans contenu.

### 8.3 Création d'un utilisateur

1. Générer l'identifiant et une DEK aléatoire de 32 octets, gardée en mémoire.
2. Chiffrer l'e-mail, le nom et le téléphone avec cette DEK ; calculer les index aveugles.
3. Insérer la ligne `users`, puis la ligne `user_keys` avec la DEK chiffrée par la KEK active. Seule la forme chiffrée de la DEK atteint la base.

### 8.4 Rotation de la KEK (F12)

1. L'exploitant ajoute `KEK_V<n+1>` dans `api/.env` et redémarre l'API. Les deux versions sont chargées.
2. L'administrateur appelle `POST /admin/keys/rotate` : la version `n` passe `RETIRED`, la version `n+1` est créée en `ACTIVE`.
3. Dans la même transaction, chaque DEK est déchiffrée avec l'ancienne KEK et rechiffrée avec la nouvelle, par lots de 500. Les messages ne sont pas touchés.
4. Quand plus aucune DEK n'utilise la version `n` (`GET /admin/keys`), l'exploitant retire `KEK_V<n>` de l'environnement.

Sans nouvelle version chargée, la route renvoie `409 KEK_NOT_PROVISIONED`.

### 8.5 Mode de démonstration (F7, F8)

Avec `DEMO_MODE=true`, les routes `/demo/*` sont montées. L'interrupteur `PUT /demo/encryption-mode` choisit si les **nouveaux** messages sont enregistrés `ENCRYPTED` ou `PLAINTEXT` ; il est gardé en mémoire et revient à `ENCRYPTED` au redémarrage. Avec `DEMO_MODE=false`, tout message est chiffré, quel que soit l'interrupteur. Les noms, e-mails et téléphones restent toujours chiffrés.

---

## 9. API REST

Toutes les routes sont préfixées par `/api/v1`. 🔒 = jeton requis.

### 9.1 Authentification et compte

| Méthode | Route | Description |
| --- | --- | --- |
| POST | `/auth/register` | Inscription d'un patient ; envoie un code ; répond toujours `202` |
| POST | `/auth/verify-email` | Vérifie le code ; active le compte et ouvre la session |
| POST | `/auth/resend-code` | Renvoie un code ; répond `202`, ou `429` si le délai n'est pas écoulé |
| POST | `/auth/accept-invitation` | Agent ou administrateur invité : code + choix du mot de passe |
| POST | `/auth/login` | Connexion ; renvoie l'utilisateur et son rôle (F14) |
| POST | `/auth/refresh` | Rotation du jeton de rafraîchissement |
| POST | `/auth/logout` | Révoque la session et efface les cookies |
| GET | `/auth/me` 🔒 | Utilisateur connecté : id, rôle, statut, e-mail, nom, téléphone |

### 9.2 Espace patient (rôle `PATIENT`, pages `/patient`)

| Méthode | Route | Description |
| --- | --- | --- |
| POST | `/conversations` 🔒 | Démarre une conversation avec un premier message (F3) |
| GET | `/conversations?cursor=&limit=` 🔒 | Historique paginé : statut, niveau, dates, sans contenu (F5) |
| GET | `/conversations/{id}` 🔒 | Une conversation avec ses messages (F5) |
| POST | `/conversations/{id}/messages` 🔒 | Envoie un message, reçoit la réponse et l'éventuelle orientation (F3, F4) |

### 9.3 Espace agent de santé (`/agent`, rôle `HEALTH_AGENT`, page `/oriagent`)

| Méthode | Route | Description |
| --- | --- | --- |
| GET | `/agent/callbacks?status=` 🔒 | Liste de rappel : nom et téléphone du patient, niveau, date (F10). Sans filtre : rappels en attente et rappels pris par l'agent |
| POST | `/agent/callbacks/{id}/assign` 🔒 | Prend un rappel `PENDING` |
| POST | `/agent/callbacks/{id}/release` 🔒 | Remet le rappel en `PENDING` |
| POST | `/agent/callbacks/{id}/close` 🔒 | Clôt en `COMPLETED` ou `UNREACHABLE`, avec note facultative |
| GET | `/agent/callbacks/{id}/conversation` 🔒 | Conversation du rappel attribué ; journalisée `conversation.read` (F11) |

### 9.4 Administration (`/admin`, rôle `ADMIN`, page `/oriadmin`)

| Domaine | Routes | Description |
| --- | --- | --- |
| Comptes | `GET /admin/users`, `POST /admin/users`, `PATCH /admin/users/{id}/status` | Liste, invitation d'un agent ou d'un administrateur, désactivation et réactivation (F15) |
| Journal | `GET /admin/audit-logs?action=&limit=` | Derniers événements du journal d'audit |
| Clés (branche chiffrée) | `GET /admin/keys`, `POST /admin/keys/rotate` | Versions de KEK, nombre de DEK par version, rotation (F12) |

### 9.5 Démonstration (`/demo`, rôle `ADMIN`, branche chiffrée, `DEMO_MODE=true`)

| Méthode | Route | Description |
| --- | --- | --- |
| GET | `/demo/encryption-mode` 🔒 | Mode courant : `ENCRYPTED` ou `PLAINTEXT` |
| PUT | `/demo/encryption-mode` 🔒 | Change le mode des nouveaux messages (F7) |
| GET | `/demo/raw/messages?limit=` 🔒 | Lignes brutes de `messages`, octets en hexadécimal (F8) |
| GET | `/demo/raw/users?limit=` 🔒 | Lignes brutes de `users`, octets en hexadécimal (F8) |

Avec `DEMO_MODE=false`, ces routes ne sont pas montées et renvoient `404 RESOURCE_NOT_FOUND`.

### 9.6 Santé

| Méthode | Route | Description |
| --- | --- | --- |
| GET | `/health/live` | Le processus répond |
| GET | `/health/ready` | La base répond |

---

## 10. Tâches planifiées

Pas de file de tâches en v1. Les tâches sont des commandes, à lancer par cron en production.

| Commande | Effet | Fréquence proposée |
| --- | --- | --- |
| `python -m app.cli mark-abandoned` | Passe en `ABANDONED` les conversations sans activité depuis `CONVERSATIONS_ABANDON_AFTER_SECONDS` | Toutes les heures |
| `python -m app.cli purge-expired` | Supprime les codes et jetons de rafraîchissement expirés depuis plus d'un jour | Tous les jours |
| `python -m app.cli create-admin` | Crée un administrateur actif | À l'installation |
| `python -m app.cli generate-keys` | Affiche de nouveaux secrets pour `api/.env` (branche chiffrée) | À l'installation |

Les e-mails partent dans le processus `api`, en tâche d'arrière-plan FastAPI, juste après la réponse HTTP.

---

## 11. Sécurité

- Transport : HTTPS obligatoire en production, cookies `Secure` (`COOKIE_SECURE=true`). En local, le navigateur ne parle qu'à Next.js, qui transmet `/api/*` à FastAPI.
- Mots de passe et jetons : §4.4 et §8.1. Comparaison des codes et des empreintes en temps constant.
- Protection contre l'énumération : `/auth/register` et `/auth/resend-code` répondent pareil qu'une adresse existe ou non ; la connexion renvoie le même message pour un e-mail inconnu et un mauvais mot de passe, avec le même temps de calcul.
- Protection contre la force brute : 5 essais par code, renvoi d'un code au plus toutes les 60 secondes et 5 fois par heure, verrouillage du compte 15 minutes après 5 échecs de connexion (proposé). La limitation par adresse IP n'est pas en v1 (§15).
- Validation des entrées : Pydantic, champs inconnus refusés, message patient limité à 2 000 caractères ; les erreurs de validation ne renvoient jamais la valeur reçue.
- Contrôle d'accès : toujours côté serveur (§4.5), jamais déduit du frontend.
- Journal d'audit : inscription, vérification, connexions et échecs, invitation, activation, désactivation, réutilisation d'un jeton de rafraîchissement, démarrage et orientation d'une conversation, prise, relâche et clôture d'un rappel, lecture d'une conversation par un agent, rotation de la KEK, changement du mode de démo.
- Journaux applicatifs : jamais de corps de requête, de prompt, de réponse du modèle, d'e-mail ni de code. Seul le type d'erreur RodiumAI est journalisé.
- Modèle d'IA : RodiumAI est une passerelle cloud vers des fournisseurs tiers. Le texte du patient quitte le serveur à chaque message. Il faut connaître la politique de conservation de RodiumAI et du modèle choisi avant toute donnée réelle (§15).
- Secrets : `api/.env` hors de Git ; `KEK_V*`, `BLIND_INDEX_KEY`, `CODE_HMAC_KEY` et `JWT_SECRET` sont des clés distinctes.
- Réglementation : Code du numérique (loi n° 2017-20) et autorisation de l'APDP au Bénin ; loi n° 2019-014 et IPDCP au Togo. Les données de santé sont des données sensibles.

---

## 12. Configuration (variables d'environnement de `api/.env`)

| Variable | Exemple / remarque |
| --- | --- |
| `APP_ENV` | `development` ; `production` désactive `/docs` |
| `DATABASE_URL` | `postgresql+psycopg://orienta:orienta@localhost:5432/orienta` ; `.../orienta_encrypted` sur la branche chiffrée |
| `FRONTEND_URL` | `http://localhost:3000` (liens dans les e-mails) |
| `JWT_SECRET` | Chaîne aléatoire d'au moins 32 caractères |
| `CODE_HMAC_KEY` | Chaîne aléatoire |
| `ACCESS_TOKEN_TTL_SECONDS` | `900` (proposé) |
| `REFRESH_TOKEN_TTL_SECONDS` | `604800` (proposé) |
| `COOKIE_SECURE` | `false` en local, `true` en production |
| `VERIFICATION_CODE_TTL_SECONDS`, `VERIFICATION_MAX_ATTEMPTS`, `VERIFICATION_RESEND_COOLDOWN_SECONDS`, `VERIFICATION_MAX_RESENDS_PER_HOUR` | `600`, `5`, `60`, `5` (proposés) |
| `AUTH_MAX_FAILED_LOGINS`, `AUTH_LOCK_DURATION_SECONDS` | `5`, `900` (proposés) |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` | `localhost`, `1025` avec Mailpit |
| `MAIL_FROM` | `Orienta <no-reply@orienta.local>` |
| `LLM_PROVIDER` | `rodiumai` ou `fake` |
| `RODIUMAI_API_KEY` | Clé RodiumAI (`rd_sk_…`) |
| `RODIUMAI_MODEL` | `openai/gpt-4o` par défaut |
| `LLM_TIMEOUT_SECONDS` | `60` |
| `TRIAGE_MAX_FOLLOW_UP_QUESTIONS` | `4` |
| `TRIAGE_RED_FLAG_KEYWORDS` | Vide ; liste séparée par des virgules, à valider par un soignant |
| `CONVERSATIONS_ABANDON_AFTER_SECONDS` | `86400` (proposé) |
| `KEK_V1`, `KEK_V2`… | Branche chiffrée : 32 octets aléatoires en base64, une variable par version |
| `BLIND_INDEX_KEY` | Branche chiffrée : 32 octets aléatoires en base64 |
| `DEMO_MODE` | Branche chiffrée : `false` ; `true` uniquement pour la démonstration |

Docker Compose a son propre fichier `.env` à la racine (identifiants PostgreSQL et pgAdmin, ports). Le frontend a `web/.env.local` (`API_URL`).

---

## 13. Qualité, tests et environnement local

- Environnement local : `docker compose up -d` lance PostgreSQL 16 (port 5432), Mailpit (SMTP 1025, boîte mail http://localhost:8025) et pgAdmin (http://localhost:5050, serveur déjà déclaré). L'API tourne dans un environnement virtuel Python (`api/.venv`), le frontend avec `npm run dev`. Le README décrit l'installation de A à Z.
- Tests (`pytest`, base `orienta_test`, modèle factice) :
    - deux branches : inscription et code, refus de connexion avant vérification, compteur d'essais, absence de fuite sur une inscription en double, refus d'un espace d'un autre rôle, parcours complet jusqu'à la clôture d'un rappel urgent, rotation et détection de réutilisation des jetons de rafraîchissement ;
    - branche chiffrée : aller-retour de chiffrement, rejet d'un texte modifié, rejet d'une AAD différente, 1 000 chiffrements du même texte tous différents, absence de texte en clair dans les tables `users` et `messages`, interrupteur de démo, rotation de la KEK sans toucher aux messages.
- Migrations : Alembic. `0001` (schéma en clair) sur les deux branches chatbot ; `0002` (chiffrement) sur la branche chiffrée, qui refuse de s'appliquer à une base contenant déjà des utilisateurs.
- CI à mettre en place (proposé) : ruff, mypy, pytest, gitleaks, bandit, pip-audit, `next build`.

---

## 14. Préparation des évolutions

| Évolution | Point d'extension prévu |
| --- | --- |
| M1 — Coffre à secrets (Vault, KMS) | Classe `EnvKekProvider` dans `app/crypto/keys.py` : une autre implémentation remplace la lecture de `KEK_V<n>` sans toucher aux modules ; `key_encryption_keys.version` reste la référence |
| M2 — Annuaire des centres de santé | Nouvelle table `health_centers` ; colonne `recommended_health_center_id` (NULL, FK) à ajouter à `conversations` ; le format de sortie du modèle (§7) accepte des champs supplémentaires |

---

## 15. Points à trancher avant développement

| # | Sujet | Impact backend |
| --- | --- | --- |
| 1 | Nom définitif du projet | Domaines, `MAIL_FROM`, noms de base |
| 2 | Date de lancement, hébergeur et pays d'hébergement (souveraineté, attente de l'IPDCP) | §12, §13 |
| 3 | Fournisseur d'e-mails de production : il verra les adresses et les codes | §2, §12 |
| 4 | Le téléphone est-il obligatoire ? Sans lui, l'agent ne peut pas rappeler (F10) | `users.phone_*`, §4.2 |
| 5 | Liste des signes d'alerte, niveau par défaut et règles d'orientation, à valider par un soignant | §7 |
| 6 | Durées et seuils marqués « proposé » (sessions, codes, verrouillage, abandon) | §4, §12 |
| 7 | Modèle RodiumAI définitif, et politique de conservation des prompts chez RodiumAI et chez le fournisseur du modèle | §2, §7, §11 |
| 8 | Durée de conservation des conversations et suppression de compte | §3.3, `user_keys` |
| 9 | Réinitialisation du mot de passe, non prévue dans le CDC | §4, `verification_purpose` |
| 10 | Limitation de débit par adresse IP (nécessite un stockage partagé, par exemple Redis, si plusieurs instances) | §11 |
| 11 | Démarches APDP (Bénin) et IPDCP (Togo) avant toute donnée réelle | §11 |

---

## 16. Ordre de développement

1. Socle (`main`) : Docker Compose, configuration, base, format d'erreur, santé, squelettes FastAPI et Next.js, README.
2. Authentification : inscription, codes par e-mail via Mailpit, connexion, rafraîchissement, rôles, redirection, journal d'audit.
3. Conversations : adaptateur RodiumAI, prompt système, pré-orientation et garde-fous.
4. Espace agent : liste de rappel, prise et clôture, lecture journalisée.
5. Administration : invitations, désactivation, journal.
6. Branche `chatbot-with-encryption` : enveloppe DEK/KEK, AAD, index aveugle, migration `0002`, rotation, module de démonstration.
7. Avant toute donnée réelle : CI, audit de sécurité, points de §15.
