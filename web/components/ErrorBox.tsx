import { errorText } from "@/lib/texts";

export function ErrorBox({ code }: { code: string | null }) {
  if (!code) return null;
  return <div className="alert error">{errorText(code)}</div>;
}
