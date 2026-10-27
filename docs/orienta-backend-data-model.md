# Orienta — Data model overview (backend)

> Companion file to `orienta-backend-tdr.md` (section 5). The full column list, types and constraints stay in the TDR; this file shows how the tables relate to each other.
> Diagrams are split by domain for readability. Only keys and the most important columns are shown.

## How to read the links

Each link carries two cardinalities written as **minimum,maximum**. Each pair sits next to the table it counts, and is read from the other table:

| Cardinality | Meaning |
| --- | --- |
| `0,1` | zero or one |
| `1,1` | exactly one |
| `0,N` | zero, one or many |
| `1,N` | at least one, possibly many |

Example: `conversations` — `"1,1 contains 1,N"` — `messages` reads:

- one conversation contains **1,N** messages;
- one message is linked to **1,1** conversation (always exactly one).

The line ends drawn by Mermaid show the same thing: a bar `|` means "one", a circle `o` means "zero is allowed", a crow's foot `{` means "many".

In the attribute lists: **PK** primary key · **FK** foreign key · **UK** unique value.

The diagrams describe the `chatbot-with-encryption` branch. Every encrypted field is stored as two columns, `<field>_ciphertext` and `<field>_nonce`; diagrams show only the `_ciphertext` column. In the `chatbot-without-encryption` branch, each pair is a single plain-text column (`users.email` UK, `users.full_name`, `users.phone`, `messages.content`, `callback_requests.outcome_note`), and the tables `user_keys` and `key_encryption_keys` do not exist (section 3 below).

---

## 1. Global map

How the domains connect, without columns.

```mermaid
erDiagram
    users ||--|| user_keys : "1,1 owns 1,1"
    key_encryption_keys ||--o{ user_keys : "1,1 wraps 0,N"
    users ||--o{ email_verification_codes : "1,1 receives 0,N"
    users ||--o{ refresh_tokens : "1,1 holds 0,N"
    users ||--o{ consents : "1,1 gives 0,N"
    users ||--o{ conversations : "1,1 starts 0,N"
    conversations ||--|{ messages : "1,1 contains 1,N"
    conversations ||--o| callback_requests : "1,1 triggers 0,1"
    users |o--o{ callback_requests : "0,1 handles 0,N"
```

---

## 2. Accounts and authentication

```mermaid
erDiagram
    users |o--o{ users : "0,1 invites 0,N"
    users ||--o{ email_verification_codes : "1,1 receives 0,N"
    users ||--o{ refresh_tokens : "1,1 holds 0,N"
    refresh_tokens |o--o| refresh_tokens : "0,1 replaced by 0,1"
    users ||--o{ consents : "1,1 gives 0,N"

    users {
        uuid id PK
        enum role "PATIENT | HEALTH_AGENT | ADMIN"
        enum status "PENDING_VERIFICATION | ACTIVE | DISABLED"
        bytea email_ciphertext "AES-256-GCM, user DEK"
        bytea email_blind_index UK "HMAC-SHA256"
        bytea full_name_ciphertext
        bytea phone_ciphertext "nullable"
        text password_hash "Argon2id, nullable until invitation accepted"
        timestamp email_verified_at
        timestamp locked_until
        uuid invited_by_id FK "nullable"
    }
    email_verification_codes {
        uuid id PK
        uuid user_id FK
        enum purpose "EMAIL_VERIFICATION | INVITATION"
        bytea code_hash "HMAC-SHA256"
        timestamp expires_at
        int attempt_count
        timestamp consumed_at
    }
    refresh_tokens {
        uuid id PK
        uuid user_id FK
        uuid family_id
        bytea token_hash UK "SHA-256"
        timestamp expires_at
        timestamp revoked_at
        uuid replaced_by_id FK, UK "nullable"
    }
    consents {
        uuid id PK
        uuid user_id FK
        text consent_version
        timestamp accepted_at
    }
```

---

## 3. Encryption keys (`chatbot-with-encryption` only)

```mermaid
erDiagram
    users ||--|| user_keys : "1,1 owns 1,1"
    key_encryption_keys ||--o{ user_keys : "1,1 wraps 0,N"

    key_encryption_keys {
        uuid id PK
        int version UK "key material in KEK_V<version>, never in the database"
        enum status "ACTIVE | RETIRED"
        timestamp activated_at
        timestamp retired_at
    }
    user_keys {
        uuid id PK
        uuid user_id FK, UK
        uuid kek_id FK
        bytea wrapped_dek "DEK encrypted by the KEK, null once destroyed"
        enum status "ACTIVE | DESTROYED"
        timestamp destroyed_at
    }
    users {
        uuid id PK
    }
```

---

## 4. Conversations and callbacks

```mermaid
erDiagram
    users ||--o{ conversations : "1,1 starts 0,N"
    conversations ||--|{ messages : "1,1 contains 1,N"
    conversations ||--o| callback_requests : "1,1 triggers 0,1"
    users |o--o{ callback_requests : "0,1 handles 0,N"

    conversations {
        uuid id PK
        uuid patient_id FK "user with role PATIENT"
        enum status "IN_PROGRESS | ORIENTED | ABANDONED"
        enum orientation_level "EMERGENCY | CONSULTATION_48H | HOME_CARE, nullable"
        int follow_up_count
        timestamp oriented_at
        timestamp last_message_at
    }
    messages {
        uuid id PK
        uuid conversation_id FK
        int sequence "unique per conversation"
        enum sender "PATIENT | ASSISTANT"
        enum encryption_mode "ENCRYPTED | PLAINTEXT"
        bytea content_ciphertext "patient DEK"
        text content_plaintext "only when ENCRYPTION_ENABLED=false"
    }
    callback_requests {
        uuid id PK
        uuid conversation_id FK, UK
        uuid assigned_agent_id FK "user with role HEALTH_AGENT, nullable"
        enum status "PENDING | ASSIGNED | COMPLETED | UNREACHABLE"
        timestamp assigned_at
        timestamp closed_at
        bytea outcome_note_ciphertext "patient DEK, nullable"
    }
    users {
        uuid id PK
        enum role "PATIENT | HEALTH_AGENT | ADMIN"
    }
```

---

## Tables without foreign keys

- `key_encryption_keys` holds only metadata about master keys; it is referenced by `user_keys` but references nothing.
- `audit_logs` stores `actor_id` and `resource_id` as plain identifiers, without foreign keys, so the audit trail survives the deletion or crypto-shredding of any account or resource.
