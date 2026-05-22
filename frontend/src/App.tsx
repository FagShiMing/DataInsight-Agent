import { useEffect, useMemo, useState } from "react";

type AnyRecord = Record<string, any>;

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

function asRecord(value: unknown): AnyRecord {
  return value && typeof value === "object" ? (value as AnyRecord) : {};
}

function asArray(value: unknown): any[] {
  return Array.isArray(value) ? value : [];
}

function stringify(value: unknown, fallback = "暂无数据") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function getShape(profile: AnyRecord) {
  const shape = asRecord(profile.shape);
  const columnsValue = shape.columns ?? profile.columns ?? profile.column_names;
  const columnsCount = Array.isArray(columnsValue) ? columnsValue.length : columnsValue;
  return {
    rows: shape.rows ?? profile.rows ?? 0,
    columns: columnsCount ?? 0,
  };
}

function getColumns(profile: AnyRecord): string[] {
  const columns = profile.columns ?? profile.column_names;
  return Array.isArray(columns) ? columns.map(String) : [];
}

async function readJsonResponse(response: Response) {
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const detail = data.detail ?? data.message ?? response.statusText;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function App() {
  const [healthStatus, setHealthStatus] = useState("正在检查后端连接...");
  const [healthLoading, setHealthLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [profile, setProfile] = useState<AnyRecord | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [suggestionSummary, setSuggestionSummary] = useState("");
  const [suggestionLoading, setSuggestionLoading] = useState(false);
  const [suggestionError, setSuggestionError] = useState("");
  const [question, setQuestion] = useState("哪些字段有缺失值？");
  const [useLlmAnswer, setUseLlmAnswer] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");
  const [chatResult, setChatResult] = useState<AnyRecord | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState("");
  const [reportMarkdown, setReportMarkdown] = useState("");
  const [copyStatus, setCopyStatus] = useState("");

  const shape = useMemo(() => getShape(profile ?? {}), [profile]);
  const columns = useMemo(() => getColumns(profile ?? {}), [profile]);
  const missingValues = asRecord(profile?.missing_values);
  const numericSummary = asRecord(profile?.numeric_summary);
  const sessionId = profile?.session_id;

  useEffect(() => {
    async function checkHealth() {
      setHealthLoading(true);
      try {
        const response = await fetch(`${API_BASE_URL}/health`);
        await readJsonResponse(response);
        setHealthStatus("后端已连接");
      } catch (error) {
        setHealthStatus(
          `后端未连接，请检查 FastAPI 是否启动。${error instanceof Error ? error.message : ""}`,
        );
      } finally {
        setHealthLoading(false);
      }
    }

    checkHealth();
  }, []);

  async function handleUpload() {
    if (!selectedFile) {
      setUploadError("请先选择 CSV 文件。");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);
    setUploadLoading(true);
    setUploadError("");
    setChatResult(null);
    setReportMarkdown("");
    setSuggestions([]);
    setSuggestionSummary("");

    try {
      const response = await fetch(`${API_BASE_URL}/profile/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await readJsonResponse(response);
      setProfile(asRecord(data));
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "上传失败");
    } finally {
      setUploadLoading(false);
    }
  }

  async function handleSuggestions() {
    if (!profile) {
      setSuggestionError("请先上传 CSV。");
      return;
    }

    setSuggestionLoading(true);
    setSuggestionError("");

    try {
      const response = await fetch(`${API_BASE_URL}/analysis/suggestions`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({session_id: sessionId, profile}),
      });
      const data = await readJsonResponse(response);
      setSuggestions(asArray(data.suggestions).map(String));
      setSuggestionSummary(String(data.summary ?? ""));
    } catch (error) {
      setSuggestionError(error instanceof Error ? error.message : "分析建议生成失败");
    } finally {
      setSuggestionLoading(false);
    }
  }

  async function handleChat() {
    if (!profile) {
      setChatError("请先上传 CSV。");
      return;
    }
    if (!question.trim()) {
      setChatError("请输入数据问题。");
      return;
    }

    setChatLoading(true);
    setChatError("");

    try {
      const response = await fetch(`${API_BASE_URL}/chat/data`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          session_id: sessionId,
          profile,
          question: question.trim(),
          use_llm_answer: useLlmAnswer,
        }),
      });
      const data = await readJsonResponse(response);
      setChatResult(asRecord(data));
    } catch (error) {
      setChatError(error instanceof Error ? error.message : "数据问答失败");
    } finally {
      setChatLoading(false);
    }
  }

  async function handleReport() {
    if (!profile) {
      setReportError("请先上传 CSV。");
      return;
    }

    setReportLoading(true);
    setReportError("");
    setCopyStatus("");

    try {
      const response = await fetch(`${API_BASE_URL}/report/generate`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          profile,
          insights: suggestions.join("\n") || undefined,
          tool_trace: chatResult?.tool_trace ?? chatResult?.trace ?? chatResult?.tool_calls ?? [],
        }),
      });
      const data = await readJsonResponse(response);
      setReportMarkdown(String(data.markdown ?? ""));
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "报告生成失败");
    } finally {
      setReportLoading(false);
    }
  }

  async function handleCopyReport() {
    if (!reportMarkdown) {
      return;
    }
    try {
      await navigator.clipboard.writeText(reportMarkdown);
      setCopyStatus("已复制");
    } catch {
      setCopyStatus("复制失败，请手动选择报告文本");
    }
  }

  const selectedTool = chatResult?.selected_tool ?? chatResult?.tool_name ?? "暂无";
  const answer =
    chatResult?.answer ?? chatResult?.final_answer ?? chatResult?.response ?? "暂无回答";
  const toolTrace =
    chatResult?.tool_trace ?? chatResult?.trace ?? chatResult?.tool_calls ?? [];
  const toolResult = chatResult?.tool_result ?? chatResult?.result ?? null;

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <h1>DataInsight-Agent</h1>
          <p>
            上传 CSV，自动生成数据画像、分析建议，并通过 Agent 工具调用回答数据问题。
          </p>
        </div>
        <span className={healthStatus === "后端已连接" ? "status ok" : "status warn"}>
          {healthLoading ? "检查中..." : healthStatus}
        </span>
      </header>

      <section className="section">
        <h2>CSV 上传</h2>
        <div className="row">
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          />
          <button onClick={handleUpload} disabled={uploadLoading}>
            {uploadLoading ? "正在上传 CSV 并生成数据画像..." : "上传并生成画像"}
          </button>
        </div>
        {uploadError && <p className="error">{uploadError}</p>}
      </section>

      <section className="section">
        <h2>数据概览</h2>
        {!profile ? (
          <p className="muted">上传 CSV 后展示数据画像。</p>
        ) : (
          <>
            <div className="metrics">
              <div>
                <span>行数</span>
                <strong>{shape.rows}</strong>
              </div>
              <div>
                <span>列数</span>
                <strong>{shape.columns}</strong>
              </div>
              <div>
                <span>session_id</span>
                <strong className="small-text">{sessionId ?? "暂无"}</strong>
              </div>
            </div>

            <h3>字段信息</h3>
            <div className="tag-list">
              {columns.length ? columns.map((column) => <span key={column}>{column}</span>) : "暂无字段"}
            </div>

            <h3>缺失值概览</h3>
            <pre>{stringify(missingValues)}</pre>

            <h3>数值列摘要</h3>
            <pre>{stringify(numericSummary)}</pre>
          </>
        )}
      </section>

      <section className="section">
        <h2>分析建议</h2>
        <button onClick={handleSuggestions} disabled={!profile || suggestionLoading}>
          {suggestionLoading ? "正在生成分析建议..." : "生成分析建议"}
        </button>
        {suggestionError && <p className="error">{suggestionError}</p>}
        {suggestionSummary && <p>{suggestionSummary}</p>}
        <ul>
          {suggestions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>

      <section className="section">
        <h2>数据问答</h2>
        <label className="field">
          <span>问题</span>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            rows={3}
          />
        </label>
        <label className="toggle">
          <input
            type="checkbox"
            checked={useLlmAnswer}
            onChange={(event) => setUseLlmAnswer(event.target.checked)}
          />
          使用 LLM 最终回答（默认关闭）
        </label>
        <button onClick={handleChat} disabled={!profile || chatLoading}>
          {chatLoading ? "Agent 正在选择工具并分析数据..." : "提交问题"}
        </button>
        {chatError && <p className="error">{chatError}</p>}
        {chatResult && (
          <div className="result-block">
            <p>
              <strong>用户问题：</strong>
              {question}
            </p>
            <p>
              <strong>selected_tool：</strong>
              {String(selectedTool)}
            </p>
            <p>
              <strong>answer：</strong>
              {String(answer)}
            </p>
            <h3>tool_trace</h3>
            <pre>{stringify(toolTrace)}</pre>
            <h3>tool_result 摘要</h3>
            <pre>{stringify(toolResult)}</pre>
          </div>
        )}
      </section>

      <section className="section">
        <h2>报告生成</h2>
        <div className="row">
          <button onClick={handleReport} disabled={!profile || reportLoading}>
            {reportLoading ? "正在生成 Markdown 分析报告..." : "生成 Markdown 报告"}
          </button>
          <button onClick={handleCopyReport} disabled={!reportMarkdown}>
            复制报告
          </button>
          {copyStatus && <span className="muted">{copyStatus}</span>}
        </div>
        {reportError && <p className="error">{reportError}</p>}
        {reportMarkdown && <pre className="report">{reportMarkdown}</pre>}
      </section>
    </main>
  );
}

export default App;
