import { apiFetch } from "@/lib/api";

export type PharmacistQuestion = {
  id: string;
  question: string;
  answer: string | null;
  is_answered: boolean;
  created_at: string;
};

export type ThreadMessage = {
  id: string;
  sender: "customer" | "pharmacist";
  body: string;
  created_at: string;
};

export type QuestionDetail = PharmacistQuestion & { thread: ThreadMessage[] };

export async function askQuestion(question: string): Promise<PharmacistQuestion> {
  return apiFetch<PharmacistQuestion>("/ask", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export async function listQuestions(): Promise<PharmacistQuestion[]> {
  return apiFetch<PharmacistQuestion[]>("/ask");
}

export async function getQuestion(id: string): Promise<QuestionDetail> {
  return apiFetch<QuestionDetail>(`/ask/${id}`);
}
