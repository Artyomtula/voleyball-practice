import { useEffect, useState } from "react";
import { apiRequest, formatTime } from "./api.js";

export default function App() {
  const [file, setFile] = useState(null);
  const [videoId, setVideoId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    setProgress(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const video = await apiRequest("/videos", { method: "POST", body: form });
      await apiRequest(`/videos/${video.id}/process`, { method: "POST" });
      setProgress(0);
      setVideoId(video.id);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  // Пока видео обрабатывается, статус задания запрашивается раз в 2 секунды
  useEffect(() => {
    if (videoId === null) return undefined;
    const stop = (message = "") => {
      setError(message);
      setVideoId(null);
      setBusy(false);
    };
    const timer = setInterval(async () => {
      try {
        const job = await apiRequest(`/videos/${videoId}/job`);
        setProgress(job.progress);
        if (job.status === "completed") {
          setResult(await apiRequest(`/videos/${videoId}/rallies`));
          stop();
        } else if (job.status === "error") {
          stop(job.error_message || "Ошибка обработки");
        }
      } catch (err) {
        stop(err.message);
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [videoId]);

  return (
    <main className="page">
      <h1>Выделение розыгрышей в волейбольном видео</h1>
      <form className="upload" onSubmit={submit}>
        <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files[0] || null)} />
        <button type="submit" disabled={!file || busy}>
          Обработать
        </button>
      </form>
      {busy && <p>{progress === null ? "Загрузка видео..." : `Обработка: ${progress}%`}</p>}
      {error && <p className="error">{error}</p>}

      {result && (
        <>
          <h2>Найдено розыгрышей: {result.rallies.length}</h2>
          {result.rallies.length > 0 && (
            <table>
              <thead>
                <tr>
                  <th>№</th>
                  <th>Начало</th>
                  <th>Конец</th>
                </tr>
              </thead>
              <tbody>
                {result.rallies.map((rally) => (
                  <tr key={rally.number}>
                    <td>{rally.number}</td>
                    <td>{formatTime(rally.start)}</td>
                    <td>{formatTime(rally.end)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </>
      )}
    </main>
  );
}
