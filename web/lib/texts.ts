// User-facing texts (French at launch). Error codes and statuses come from the API in English.

export const ERROR_MESSAGES: Record<string, string> = {
  VALIDATION_ERROR: "Certains champs sont invalides. Vérifiez votre saisie.",
  INVALID_CREDENTIALS: "E-mail ou mot de passe incorrect.",
  EMAIL_NOT_VERIFIED: "Votre adresse e-mail n'est pas encore vérifiée.",
  ACCOUNT_DISABLED: "Ce compte est désactivé.",
  ACCOUNT_LOCKED: "Trop de tentatives. Réessayez dans quelques minutes.",
  VERIFICATION_CODE_INVALID: "Code incorrect.",
  VERIFICATION_CODE_EXPIRED: "Ce code a expiré. Demandez-en un nouveau.",
  RATE_LIMITED: "Veuillez patienter avant de réessayer.",
  CONVERSATION_CLOSED: "Cette conversation est terminée.",
  CALLBACK_ALREADY_ASSIGNED: "Ce rappel est déjà pris par un autre agent.",
  LLM_UNAVAILABLE: "L'assistant est momentanément indisponible. Réessayez dans un instant.",
  EMAIL_ALREADY_REGISTERED: "Un compte existe déjà pour cette adresse.",
  INVALID_TRANSITION: "Cette action n'est pas possible dans l'état actuel.",
};

export function errorText(code: string): string {
  return ERROR_MESSAGES[code] ?? "Une erreur est survenue. Réessayez.";
}

export const ORIENTATION_LABELS: Record<string, string> = {
  EMERGENCY: "Urgence",
  CONSULTATION_48H: "Consultation sous 48 h",
  HOME_CARE: "Conseils à domicile",
};

export const ORIENTATION_ADVICE: Record<string, string> = {
  EMERGENCY: "Rendez-vous aux urgences les plus proches ou appelez les secours. Un agent de santé va vous rappeler.",
  CONSULTATION_48H: "Consultez un centre de santé dans les 48 heures.",
  HOME_CARE: "Suivez les conseils ci-dessus et consultez si les symptômes persistent ou s'aggravent.",
};

export const STATUS_LABELS: Record<string, string> = {
  IN_PROGRESS: "En cours",
  ORIENTED: "Orientée",
  ABANDONED: "Abandonnée",
  PENDING: "En attente",
  ASSIGNED: "Pris en charge",
  COMPLETED: "Patient joint",
  UNREACHABLE: "Injoignable",
  PENDING_VERIFICATION: "En attente de vérification",
  ACTIVE: "Actif",
  DISABLED: "Désactivé",
};

export const ROLE_LABELS: Record<string, string> = {
  PATIENT: "Patient",
  HEALTH_AGENT: "Agent de santé",
  ADMIN: "Administrateur",
};

export const DISCLAIMER = "Orienta ne remplace pas un professionnel de santé et ne pose aucun diagnostic.";

export const CONSENT_VERSION = "2026-10";

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}
