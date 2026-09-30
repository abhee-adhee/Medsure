import React, { useState, useEffect } from 'react';

const API_BASE = "http://localhost:8000";

export default function App() {
  const [activeTab, setActiveTab] = useState('scan');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [alerts, setAlerts] = useState([]);

  // Manual Form
  const [manual, setManual] = useState({
    medicine_name: '', batch_number: '', expiry_date: '', gtin: '', serial: ''
  });

  const handleFile = (e) => {
    const f = e.target.files[0];
    if (f) {
      setFile(f);
      setPreview(URL.createObjectURL(f));
    }
  };

  const runScan = async () => {
    if (!file) { alert("Please select an image file first."); return; }
    setLoading(true);
    const fd = new FormData();
    fd.append("image", file);
    try {
      const res = await fetch(`${API_BASE}/scan`, {
        method: "POST",
        headers: { "X-Device-Token": "dev_react_ui" },
        body: fd
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      alert("Scan failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const runManual = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/scan/manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Device-Token": "dev_react_ui" },
        body: JSON.stringify(manual)
      });
      const data = await res.json();
      setResult(data);
      setActiveTab('scan');
    } catch (err) {
      alert("Manual scan failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const runDemo = async (caseId) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/demo/${caseId}`);
      const data = await res.json();
      setResult(data);
      setActiveTab('scan');
    } catch (err) {
      alert("Demo failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'alerts') {
      fetch(`${API_BASE}/alerts`).then(r => r.json()).then(d => setAlerts(d.alerts || []));
    }
    if (activeTab === 'stats') {
      fetch(`${API_BASE}/stats`).then(r => r.json()).then(d => setStats(d));
    }
  }, [activeTab]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans">
      <header className="bg-indigo-900 text-white shadow-md py-4 px-6 flex items-center justify-between">
        <div class="flex items-center space-x-3">
          <i className="fa-solid fa-shield-halved text-emerald-400 text-2xl"></i>
          <div>
            <h1 className="text-xl font-bold">MedSure Vision</h1>
            <p className="text-xs text-indigo-200">Medicine Packaging Screening & Authentication Engine</p>
          </div>
        </div>
        <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-3 py-1 rounded-full flex items-center">
          <span className="w-2 h-2 mr-1.5 bg-emerald-400 rounded-full animate-pulse"></span> Connected to Backend (8000)
        </span>
      </header>

      <nav className="bg-white border-b border-slate-200 px-6 flex space-x-6 text-sm">
        {['scan', 'manual', 'demo', 'alerts', 'stats'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`py-3 font-semibold capitalize border-b-2 ${activeTab === tab ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
          >
            {tab === 'scan' ? 'Verification Scan' : tab === 'manual' ? 'Manual Entry' : tab === 'demo' ? 'Demo Cases' : tab === 'alerts' ? 'Active Alerts' : 'Stats'}
          </button>
        ))}
      </nav>

      <main className="max-w-6xl mx-auto w-full p-6 flex-1">
        {activeTab === 'scan' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
              <h2 className="font-bold text-slate-800">Package Image Input</h2>
              <input type="file" onChange={handleFile} accept="image/*" className="text-xs" />
              {preview && <img src={preview} alt="Preview" className="w-full max-h-48 object-cover rounded border" />}
              <button onClick={runScan} disabled={loading} className="w-full py-2 bg-emerald-600 text-white font-semibold text-sm rounded hover:bg-emerald-700">
                {loading ? 'Processing Multi-Layer Scan...' : 'Execute Scan'}
              </button>
            </div>

            <div className="md:col-span-2 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
              {!result ? (
                <div className="text-center py-16 text-slate-400">
                  <i className="fa-solid fa-microscope text-5xl mb-2 text-slate-300"></i>
                  <p>No analysis performed yet.</p>
                </div>
              ) : (
                <div className="space-y-4 text-xs">
                  <div className="flex items-center justify-between border-b pb-3">
                    <div>
                      <span className="font-bold uppercase text-sm px-3 py-1 rounded bg-indigo-100 text-indigo-800">{result.verdict_label}</span>
                      <p className="text-slate-500 mt-1">ID: {result.id} | {result.timestamp}</p>
                    </div>
                    <a href={`${API_BASE}/scans/${result.id}/report.pdf`} target="_blank" rel="noreferrer" className="px-3 py-1.5 bg-indigo-600 text-white rounded font-semibold">Download PDF</a>
                  </div>
                  <div className="bg-slate-50 p-3 rounded border">
                    <p className="font-semibold">Confidence: {result.confidence}%</p>
                    <p className="text-slate-600">{result.confidence_note}</p>
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-700 uppercase mb-1">Extracted Fields</h4>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2 border rounded"><b>Name:</b> {result.fields.medicine_name || 'N/A'}</div>
                      <div className="p-2 border rounded"><b>Batch:</b> {result.fields.batch_number || 'N/A'}</div>
                      <div className="p-2 border rounded"><b>Expiry:</b> {result.fields.expiry_date || 'N/A'}</div>
                      <div className="p-2 border rounded"><b>GTIN:</b> {result.code_data.gtin || 'N/A'}</div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-700 uppercase mb-1">Findings / Reasons</h4>
                    <ul className="list-disc pl-4 space-y-1">
                      {result.reasons.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  </div>
                  <p className="text-slate-400 italic pt-2">{result.disclaimer}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'manual' && (
          <form onSubmit={runManual} className="max-w-md mx-auto bg-white p-6 rounded-xl border space-y-4">
            <h2 className="font-bold text-slate-800 border-b pb-2">Manual Verification Entry</h2>
            <input placeholder="Medicine Name" value={manual.medicine_name} onChange={e => setManual({...manual, medicine_name: e.target.value})} className="w-full p-2 border rounded text-xs" />
            <input placeholder="Batch Number" value={manual.batch_number} onChange={e => setManual({...manual, batch_number: e.target.value})} className="w-full p-2 border rounded text-xs" />
            <input placeholder="Expiry Date (YYYY-MM-DD)" value={manual.expiry_date} onChange={e => setManual({...manual, expiry_date: e.target.value})} className="w-full p-2 border rounded text-xs" />
            <input placeholder="GTIN" value={manual.gtin} onChange={e => setManual({...manual, gtin: e.target.value})} className="w-full p-2 border rounded text-xs" />
            <input placeholder="Serial Number" value={manual.serial} onChange={e => setManual({...manual, serial: e.target.value})} className="w-full p-2 border rounded text-xs" />
            <button type="submit" className="w-full py-2 bg-indigo-600 text-white rounded text-xs font-semibold">Run Manual Verification</button>
          </form>
        )}

        {activeTab === 'demo' && (
          <div className="bg-white p-6 rounded-xl border space-y-4">
            <h2 className="font-bold text-slate-800">Preconfigured Demo Cases</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {['genuine', 'expiry_tampered', 'logo_shifted', 'clone_code', 'alert_match', 'blurry'].map(c => (
                <button key={c} onClick={() => runDemo(c)} className="p-3 bg-slate-50 border rounded text-xs font-medium hover:bg-indigo-50 capitalize">
                  {c.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'alerts' && (
          <div className="bg-white p-6 rounded-xl border space-y-3">
            <h2 className="font-bold text-slate-800">Active Drug Control Alerts</h2>
            {alerts.map(a => (
              <div key={a.id} className="p-3 bg-red-50 border border-red-200 rounded text-xs space-y-1">
                <div className="flex justify-between font-bold text-red-900">
                  <span>{a.medicine_name} (Batch: {a.batch_number})</span>
                  <span className="uppercase px-2 bg-red-200 rounded">{a.risk_level}</span>
                </div>
                <p className="text-red-700">{a.description}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'stats' && stats && (
          <div className="grid grid-cols-4 gap-4 text-center">
            <div className="bg-white p-4 rounded border"><p className="text-2xl font-bold">{stats.total_scans}</p><p className="text-xs text-slate-500">Total Scans</p></div>
            <div className="bg-white p-4 rounded border text-emerald-600"><p className="text-2xl font-bold">{stats.verdict_counts.low_risk}</p><p className="text-xs text-slate-500">Low Risk</p></div>
            <div className="bg-white p-4 rounded border text-amber-600"><p className="text-2xl font-bold">{stats.verdict_counts.needs_verification}</p><p class="text-xs text-slate-500">Needs Verification</p></div>
            <div className="bg-white p-4 rounded border text-red-600"><p className="text-2xl font-bold">{stats.verdict_counts.high_suspicion}</p><p className="text-xs text-slate-500">High Suspicion</p></div>
          </div>
        )}
      </main>
    </div>
  );
}
