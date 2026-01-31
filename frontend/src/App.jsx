import { useMemo, useState } from "react";
import Papa from "papaparse";
import * as XLSX from "xlsx";

const DEFAULT_COLUMNS = ["Participant_ID", "Expertise", "Lived_Experience", "Minnesota"];
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const emptyRow = (columns) =>
  columns.reduce((acc, column) => {
    acc[column] = "";
    return acc;
  }, {});

const normalizeRows = (rows, columns) =>
  rows.map((row) => {
    const normalized = { ...emptyRow(columns), ...row };
    return normalized;
  });

const parseCsv = (file) =>
  new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => resolve(results.data),
      error: (err) => reject(err)
    });
  });

const parseXlsx = async (file) => {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: "array" });
  const sheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json(sheet, { defval: "" });
};

export default function App() {
  const [mode, setMode] = useState("upload");
  const [columns, setColumns] = useState(DEFAULT_COLUMNS);
  const [rows, setRows] = useState([emptyRow(DEFAULT_COLUMNS)]);
  const [groupSize, setGroupSize] = useState(5);
  const [results, setResults] = useState(null);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  const totalParticipants = useMemo(
    () => rows.filter((row) => String(row.Participant_ID || "").trim() !== "").length,
    [rows]
  );

  const handleFile = async (file) => {
    if (!file) return;
    setError("");
    setStatus("parsing");
    try {
      const rawRows = file.name.endsWith(".csv")
        ? await parseCsv(file)
        : await parseXlsx(file);

      const detectedColumns = Array.from(
        new Set([...DEFAULT_COLUMNS, ...rawRows.flatMap((row) => Object.keys(row))])
      );
      const normalized = normalizeRows(rawRows, detectedColumns);
      setColumns(detectedColumns);
      setRows(normalized.length ? normalized : [emptyRow(detectedColumns)]);
      setResults(null);
      setStatus("ready");
    } catch (parseError) {
      setStatus("error");
      setError("We could not read that file. Please upload a .csv or .xlsx file.");
    }
  };

  const updateCell = (rowIndex, column, value) => {
    setRows((prev) =>
      prev.map((row, idx) => (idx === rowIndex ? { ...row, [column]: value } : row))
    );
  };

  const addRow = () => {
    setRows((prev) => [...prev, emptyRow(columns)]);
  };

  const addColumn = () => {
    const name = window.prompt("New column name");
    if (!name || columns.includes(name)) return;
    setColumns((prev) => [...prev, name]);
    setRows((prev) => prev.map((row) => ({ ...row, [name]: "" })));
  };

  const runModel = async () => {
    setError("");
    setStatus("running");
    try {
      const response = await fetch(`${API_BASE}/api/groups`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          participants: rows,
          group_size: groupSize,
          id_column: "Participant_ID"
        })
      });

      if (!response.ok) {
        const detail = await response.json();
        throw new Error(detail?.detail || "The backend could not complete the request.");
      }

      const data = await response.json();
      setResults(data);
      setStatus("success");
    } catch (runError) {
      setStatus("error");
      setError(runError.message || "Unable to reach the backend.");
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <div>
          <p className="badge">Diversity-first grouping</p>
          <h1>Group Formation Studio</h1>
          <p className="subtitle">
            Upload your participant list or edit it inline, then generate balanced groups with the
            Python optimization engine.
          </p>
        </div>
        <div className="hero-card">
          <div>
            <h3>Live impact preview</h3>
            <p>Track how many participants and attributes are ready before you run the model.</p>
          </div>
          <div className="hero-metrics">
            <div>
              <span className="metric-value">{totalParticipants}</span>
              <span className="metric-label">Participants</span>
            </div>
            <div>
              <span className="metric-value">{columns.length - 1}</span>
              <span className="metric-label">Attributes</span>
            </div>
          </div>
        </div>
      </header>

      <section className="steps">
        <div>
          <span className="step-number">01</span>
          <h4>Provide data</h4>
          <p>Upload CSV/XLSX or paste directly into the table to keep control of your schema.</p>
        </div>
        <div>
          <span className="step-number">02</span>
          <h4>Review & refine</h4>
          <p>Ensure IDs and attributes are complete so the solver can maximize diversity.</p>
        </div>
        <div>
          <span className="step-number">03</span>
          <h4>Generate groups</h4>
          <p>Send your data to the Python backend and receive group assignments instantly.</p>
        </div>
      </section>

      <section className="workspace">
        <div className="panel">
          <div className="panel-header">
            <h2>Participant intake</h2>
            <div className="tabs">
              <button
                className={mode === "upload" ? "active" : ""}
                onClick={() => setMode("upload")}
              >
                Upload sheet
              </button>
              <button
                className={mode === "manual" ? "active" : ""}
                onClick={() => setMode("manual")}
              >
                Edit table
              </button>
            </div>
          </div>

          {mode === "upload" ? (
            <div className="upload">
              <label className="upload-card">
                <input
                  type="file"
                  accept=".csv,.xlsx"
                  onChange={(event) => handleFile(event.target.files?.[0])}
                />
                <div>
                  <h3>Drop your file here</h3>
                  <p>We support .csv and .xlsx. Your data stays local until you hit “Run model”.</p>
                </div>
              </label>
              {status === "parsing" && <p className="hint">Parsing file…</p>}
              {error && <p className="error">{error}</p>}
            </div>
          ) : (
            <div className="manual">
              <div className="table-actions">
                <button onClick={addRow}>Add row</button>
                <button className="secondary" onClick={addColumn}>
                  Add attribute column
                </button>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {columns.map((column) => (
                        <th key={column}>{column}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, rowIndex) => (
                      <tr key={`row-${rowIndex}`}>
                        {columns.map((column) => (
                          <td key={`${rowIndex}-${column}`}>
                            <input
                              value={row[column]}
                              onChange={(event) =>
                                updateCell(rowIndex, column, event.target.value)
                              }
                              placeholder={column === "Participant_ID" ? "Required" : ""}
                            />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <div className="panel">
          <h2>Model controls</h2>
          <p className="panel-copy">
            Tune group size and launch the solver. The backend will aim to balance attribute
            representation across tables.
          </p>
          <div className="form-row">
            <label>Target group size</label>
            <input
              type="number"
              min="2"
              max="50"
              value={groupSize}
              onChange={(event) => setGroupSize(Number(event.target.value))}
            />
          </div>
          <button className="primary" onClick={runModel}>
            Run model
          </button>
          {status === "running" && <p className="hint">Optimizing group balance…</p>}
          {error && <p className="error">{error}</p>}

          {results && (
            <div className="results">
              <div className="results-header">
                <h3>Group assignments</h3>
                <p>
                  {results.stats.total_participants} participants · {results.stats.groups} groups
                </p>
              </div>
              <div className="group-grid">
                {results.groups.map((group) => (
                  <div key={group.group_id} className="group-card">
                    <h4>Group {group.group_id}</h4>
                    <ul>
                      {group.participants.map((participant) => (
                        <li key={`${group.group_id}-${participant.Participant_ID}`}>
                          <strong>{participant.Participant_ID}</strong>
                          <span>
                            {columns
                              .filter((column) => column !== "Participant_ID")
                              .map((column) => participant[column])
                              .filter(Boolean)
                              .join(" · ")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      <footer>
        <p>
          Deploy the frontend to Vercel and point <code>VITE_API_BASE_URL</code> to your Python
          backend.
        </p>
      </footer>
    </div>
  );
}
