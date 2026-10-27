import { Message } from "@/lib/types";

export function Chat({ messages }: { messages: Message[] }) {
  return (
    <div className="chat">
      {messages.map((m) => (
        <div key={m.id} className={`bubble ${m.sender}`}>
          {m.content}
        </div>
      ))}
    </div>
  );
}
