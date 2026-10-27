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
  CONSULTATION_48H: "Consultation 48 h",
  HOME_CARE: "Domicile",
};

export const ORIENTATION_ADVICE: Record<string, string> = {
  EMERGENCY: "Rendez-vous aux urgences les plus proches ou appelez les secours.",
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
  PENDING_VERIFICATION: "Non vérifié",
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

export const LEVEL_BADGE: Record<string, string> = { EMERGENCY: "orange", CONSULTATION_48H: "blue", HOME_CARE: "teal" };
export const STATUS_BADGE: Record<string, string> = {
  IN_PROGRESS: "blue", ORIENTED: "teal", ABANDONED: "", PENDING: "orange", ASSIGNED: "blue", COMPLETED: "teal",
  UNREACHABLE: "", ACTIVE: "teal", PENDING_VERIFICATION: "orange", DISABLED: "",
};

export function waiting(minutes: number | null): string {
  if (minutes === null) return "";
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  return `${h} h ${String(minutes % 60).padStart(2, "0")}`;
}
