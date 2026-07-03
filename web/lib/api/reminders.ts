import { apiFetch } from "@/lib/api";

export type ReminderStatus = "ACTIVE" | "PAUSED" | "STOPPED" | "COMPLETED";
export type ReminderSource = "CUSTOMER" | "PHARMACIST";
export type DoseStatus = "UPCOMING" | "SENT" | "MISSED";

export type DoseLog = {
  time: string;
  status: DoseStatus;
};

export type MedicationReminder = {
  id: string;
  medicine_name: string;
  instructions_text: string | null;
  times: string[];
  start_date: string;
  end_date: string | null;
  status: ReminderStatus;
  source: ReminderSource;
  next_run_at: string | null;
  created_at: string;
  today_log?: DoseLog[];
};

export type CreateReminderPayload = {
  medicine_name: string;
  instructions_text?: string;
  times: string[];
  start_date: string;
  end_date?: string;
  timezone?: string;
};

export async function listReminders(): Promise<MedicationReminder[]> {
  return apiFetch<MedicationReminder[]>("/reminders");
}

export async function listTodayReminders(): Promise<MedicationReminder[]> {
  return apiFetch<MedicationReminder[]>("/reminders?today=true");
}

export async function getReminder(id: string): Promise<MedicationReminder> {
  return apiFetch<MedicationReminder>(`/reminders/${id}`);
}

export async function createReminder(
  data: CreateReminderPayload
): Promise<MedicationReminder> {
  return apiFetch<MedicationReminder>("/reminders", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function pauseReminder(id: string): Promise<MedicationReminder> {
  return apiFetch<MedicationReminder>(`/reminders/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ action: "pause" }),
  });
}

export async function resumeReminder(id: string): Promise<MedicationReminder> {
  return apiFetch<MedicationReminder>(`/reminders/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ action: "resume" }),
  });
}

export async function stopReminder(id: string): Promise<MedicationReminder> {
  return apiFetch<MedicationReminder>(`/reminders/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ action: "stop" }),
  });
}

export async function deleteReminder(id: string): Promise<void> {
  return apiFetch<void>(`/reminders/${id}`, { method: "DELETE" });
}
