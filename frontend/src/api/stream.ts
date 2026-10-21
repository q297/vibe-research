import { API_BASE, type Schemas, tokenStore } from "./client";

type StreamHandlers = {
  onStep: (step: Schemas["TraceStep"]) => void;
  onJob: (job: Schemas["Job"]) => void;
};

// EventSource cannot send the Authorization header, so SSE is read through fetch
export async function streamJob(jobId: string, handlers: StreamHandlers, signal: AbortSignal) {
  const token = tokenStore.get();
  const response = await fetch(`${API_BASE}/v1/jobs/${jobId}/stream`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal,
  });
  if (!response.ok || !response.body) throw new Error(`Stream failed: ${response.status}`);

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) >= 0) {
      const chunk = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      let event = "message";
      let data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data += line.slice(6);
      }
      if (!data) continue;
      if (event === "step") handlers.onStep(JSON.parse(data));
      else if (event === "job") handlers.onJob(JSON.parse(data));
    }
  }
}
