import React, { useState, useEffect } from 'react';

export default function App() {
  const [apiBase, setApiBase] = useState(localStorage.getItem('medsure_api_base') || "http://localhost:8000");
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

  const saveApiBase = (url) => {
    setApiBase(url);
    localStorage.setItem('medsure_api_base', url);
  };

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
      const res = await fetch(`${apiBase}/scan`, {
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
      const res = await fetch(`${apiBase}/scan/manual`, {
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
      const res = await fetch(`${apiBase}/demo/${caseId}`);
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
      fetch(`${apiBase}/alerts`).then(r => r.json()).then(d => setAlerts(d.alerts || [])).catch(() => {});
    }
    if (activeTab === 'stats') {
      fetch(`${apiBase}/stats`).then(r => r.json()).then(d => setStats(d)).catch(() => {});
    }
  }, [activeTab, apiBase]);

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 flex flex-col font-sans">
      <header className="bg-slate-900 text-white shadow-md py-4 px-6 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg">
            <i className="fa-solid fa-shield-virus text-xl"></i>
          </div>
          <div>
            <h1 className="text-lg font-bold">MedSure Vision</h1>
            <p className="text-xs text-slate-400">Pharmaceutical Packaging Screening Platform</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1.5 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700 text-xs">
            <span className="text-slate-400 font-semibold">API Endpoint:</span>
            <input
              type="text"
              value={apiBase}
              onChange={(e) => saveApiBase(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 px-2 py-0.5 rounded text-xs focus:outline-none w-48"
            />
          </div>
        </div>
      </header>

      <nav className="bg-slate-800 border-b border-slate-700 px-6 flex space-x-6 text-xs font-semibold">
        {['scan', 'manual', 'demo', 'alerts', 'stats'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`py-3 capitalize border-b-2 transition ${activeTab === tab ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-200'}`}
          >
            {tab === 'scan' ? 'Verification Scan' : tab === 'manual' ? 'Manual Entry' : tab === 'demo' ? 'Demo Test Suite' : tab === 'alerts' ? 'Drug Alerts' : 'Dashboard Stats'}
          </button>
        ))}
      </nav>

      <main className="max-w-6xl mx-auto w-full p-6 flex-1">
        {activeTab === 'scan' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h2 className="font-bold text-slate-800 text-sm">Packaging Photo</h2>
              <input type="file" onChange={handleFile} accept="image/*" className="text-xs" />
              {preview && <img src={preview} alt="Preview" className="w-full max-h-48 object-cover rounded-xl border" />}
              <button onClick={runScan} disabled={loading} className="w-full py-3 bg-indigo-600 text-white font-semibold text-xs rounded-xl shadow hover:bg-indigo-700 transition">
                {loading ? 'Processing Multi-Layer Scan...' : 'Execute Scan Pipeline'}
              </button>
            </div>

            <div className="md:col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              {!result ? (
                <div className="text-center py-16 text-slate-400">
                  <i className="fa-solid fa-microscope text-5xl mb-2 text-slate-300"></i>
                  <p className="text-sm font-semibold">No analysis performed yet.</p>
                </div>
              ) : (
                <div className="space-y-4 text-xs">
                  <div className="flex items-center justify-between border-b pb-3">
                    <div>
                      <span className="font-bold uppercase text-xs px-3 py-1 rounded-full bg-indigo-100 text-indigo-800">{result.verdict_label}</span>
                      <p className="text-slate-400 mt-1">ID: {result.id} | {result.timestamp}</p>
                    </div>
                    <a href={`${apiBase}/scans/${result.id}/report.pdf`} target="_blank" rel="noreferrer" className="px-3.5 py-2 bg-slate-900 text-white rounded-xl font-semibold hover:bg-slate-800 transition">Export PDF</a>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border">
                    <p className="font-bold text-slate-700">Confidence Rating: {result.confidence}%</p>
                    <p className="text-slate-600">{result.confidence_note}</p>
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-500 uppercase mb-1">Extracted Product Data</h4>
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2.5 border rounded-xl bg-white"><b>Medicine:</b> {result.fields.medicine_name || 'Unverified'}</div>
                      <div className="p-2.5 border rounded-xl bg-white"><b>Batch:</b> {result.fields.batch_number || 'Unverified'}</div>
                      <div className="p-2.5 border rounded-xl bg-white"><b>Expiry:</b> {result.fields.expiry_date || 'Unverified'}</div>
                      <div className="p-2.5 border rounded-xl bg-white"><b>GTIN:</b> {result.code_data.gtin || 'N/A'}</div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-bold text-slate-500 uppercase mb-1">Pipeline Findings & Reasons</h4>
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
          <form onSubmit={runManual} className="max-w-md mx-auto bg-white p-6 rounded-2xl border space-y-4">
            <h2 className="font-bold text-slate-800 border-b pb-2 text-sm">Manual Verification Entry</h2>
            <input placeholder="Medicine Name" value={manual.medicine_name} onChange={e => setManual({...manual, medicine_name: e.target.value})} className="w-full p-2.5 border rounded-lg text-xs" />
            <input placeholder="Batch Number" value={manual.batch_number} onChange={e => setManual({...manual, batch_number: e.target.value})} className="w-full p-2.5 border rounded-lg text-xs" />
            <input placeholder="Expiry Date (YYYY-MM-DD)" value={manual.expiry_date} onChange={e => setManual({...manual, expiry_date: e.target.value})} className="w-full p-2.5 border rounded-lg text-xs" />
            <input placeholder="GTIN" value={manual.gtin} onChange={e => setManual({...manual, gtin: e.target.value})} className="w-full p-2.5 border rounded-lg text-xs" />
            <input placeholder="Serial Number" value={manual.serial} onChange={e => setManual({...manual, serial: e.target.value})} className="w-full p-2.5 border rounded-lg text-xs" />
            <button type="submit" className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-xs font-semibold hover:bg-indigo-700">Run Verification Engine</button>
          </form>
        )}

        {activeTab === 'demo' && (
          <div className="bg-white p-6 rounded-2xl border space-y-4">
            <h2 className="font-bold text-slate-800 text-sm">Synthetic Test Case Matrix</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {['genuine', 'expiry_tampered', 'logo_shifted', 'clone_code', 'alert_match', 'blurry'].map(c => (
                <button key={c} onClick={() => runDemo(c)} className="p-3 bg-slate-50 border rounded-xl text-xs font-medium hover:bg-indigo-50 capitalize text-left">
                  {c.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'alerts' && (
          <div className="bg-white p-6 rounded-2xl border space-y-3">
            <h2 className="font-bold text-slate-800 text-sm">Active Drug Control Alerts</h2>
            {alerts.map(a => (
              <div key={a.id} className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs space-y-1">
                <div className="flex justify-between font-bold text-red-900">
                  <span>{a.medicine_name} (Batch: {a.batch_number})</span>
                  <span className="uppercase px-2 bg-red-200 rounded text-[10px]">{a.risk_level}</span>
                </div>
                <p className="text-red-700">{a.description}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'stats' && stats && (
          <div className="grid grid-cols-4 gap-4 text-center">
            <div className="bg-white p-5 rounded-2xl border"><p className="text-2xl font-bold">{stats.total_scans}</p><p className="text-xs text-slate-400 font-bold uppercase mt-1">Total Scans</p></div>
            <div className="bg-white p-5 rounded-2xl border text-emerald-600"><p className="text-2xl font-bold">{stats.verdict_counts.low_risk}</p><p className="text-xs text-slate-400 font-bold uppercase mt-1">Low Risk</p></div>
            <div className="bg-white p-5 rounded-2xl border text-amber-500"><p className="text-2xl font-bold">{stats.verdict_counts.needs_verification}</p><p className="text-xs text-slate-400 font-bold uppercase mt-1">Needs Verification</p></div>
            <div className="bg-white p-5 rounded-2xl border text-red-600"><p className="text-2xl font-bold">{stats.verdict_counts.high_suspicion}</p><p className="text-xs text-slate-400 font-bold uppercase mt-1">High Suspicion</p></div>
          </div>
        )}
      </main>
    </div>
  );
}
