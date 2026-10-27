export interface Message {
  id: string;
  sequence: number;
  sender: "PATIENT" | "ASSISTANT";
  content: string;
  createdAt: string;
}

export interface ConversationSummary {
  id: string;
  status: "IN_PROGRESS" | "ORIENTED" | "ABANDONED";
  orientationLevel: "EMERGENCY" | "CONSULTATION_48H" | "HOME_CARE" | null;
  createdAt: string;
  lastMessageAt: string;
}

export interface Conversation extends ConversationSummary {
  messages: Message[];
}

export interface Callback {
  id: string;
  status: "PENDING" | "ASSIGNED" | "COMPLETED" | "UNREACHABLE";
  conversationId: string;
  orientationLevel: string | null;
  patientName: string;
  patientPhone: string | null;
  assignedToMe: boolean;
  createdAt: string;
  closedAt: string | null;
  outcomeNote: string | null;
}
