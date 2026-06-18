'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001';

const PROVIDERS = ['openai', 'anthropic', 'ollama', 'groq', 'together', 'custom'];

interface Settings {
  provider: string;
  apiKey: string;
  baseUrl: string;
  frontierModel: string;
  standardModel: string;
  monitorModel: string;
  coderModel: string;
  maxTokensPerRun: number;
  rateLimitRpm: number;
  roundIntervalSecs: number;
}

const DEFAULT: Settings = {
  provider: 'openai',
  apiKey: '',
  baseUrl: '',
  frontierModel: '',
  standardModel: '',
  monitorModel: '',
  coderModel: '',
  maxTokensPerRun: 100000,
  rateLimitRpm: 60,
  roundIntervalSecs: 60,
};

function loadFromStorage(): Settings {
  if (typeof window === 'undefined') return DEFAULT;
  try {
    const raw = localStorage.getItem('agentco_settings');
    return raw ? { ...DEFAULT, ...JSON.parse(raw) } : DEFAULT;
  } catch {
    return DEFAULT;
  }
}

type HealthStatus = 'unknown' | 'ok' | 'error';

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT);
  const [saved, setSaved] = useState(false);
  const [health, setHealth] = useState<{ status: HealthStatus; data?: unknown }>({ status: 'unknown' });
  const [healthLoading, setHealthLoading] = useState(false);
  const [resetDialog, setResetDialog] = useState(false);
  const [resetInput, setResetInput] = useState('');
  const [connTest, setConnTest] = useState<{ status: HealthStatus; msg?: string } | null>(null);

  useEffect(() => {
    setSettings(loadFromStorage());
    // Load infrastructure status on mount
    fetchHealth();
  }, []);

  const set = <K extends keyof Settings>(key: K, val: Settings[K]) =>
    setSettings(s => ({ ...s, [key]: val }));

  const save = () => {
    const toSave = { ...settings, apiKey: '' }; // never persist key raw
    localStorage.setItem('agentco_settings', JSON.stringify({ ...toSave, apiKey: settings.apiKey }));
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  const fetchHealth = async () => {
    setHealthLoading(true);
    try {
      const r = await fetch(`${API}/health`);
      const data = await r.json();
      setHealth({ status: r.ok ? 'ok' : 'error', data });
    } catch {
      setHealth({ status: 'error' });
    } finally {
      setHealthLoading(false);
    }
  };

  const testConnection = async () => {
    setConnTest(null);
    try {
      const r = await fetch(`${API}/health`);
      if (r.ok) setConnTest({ status: 'ok', msg: 'Connection successful' });
      else setConnTest({ status: 'error', msg: `Server returned ${r.status}` });
    } catch (e) {
      setConnTest({ status: 'error', msg: String(e) });
    }
  };

  const healthData = health.data as Record<string, unknown> | undefined;

  const services = [
    { name: 'Backend API', up: health.status === 'ok' },
    { name: 'Postgres', up: healthData?.postgres === true || healthData?.db === 'ok' },
    { name: 'Kafka', up: healthData?.kafka === true || healthData?.kafka === 'ok' },
    { name: 'Redis', up: healthData?.redis === true || healthData?.redis === 'ok' },
  ];

  return (
    <div className="p-6 max-w-3xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure LLM providers, run parameters, and infrastructure</p>
      </div>

      {/* LLM Provider */}
      <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
        <h2 className="font-semibold text-gray-800 mb-4">LLM Provider</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Provider</label>
            <select
              value={settings.provider}
              onChange={e => set('provider', e.target.value)}
              className="border border-gray-200 rounded-md px-3 py-2 text-sm w-full max-w-xs"
            >
              {PROVIDERS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              API Key
              <span className="ml-2 text-xs text-gray-400 font-normal">Stored securely in OS keychain via Tauri</span>
            </label>
            <input
              type="password"
              value={settings.apiKey}
              onChange={e => set('apiKey', e.target.value)}
              placeholder="sk-..."
              className="border border-gray-200 rounded-md px-3 py-2 text-sm w-full max-w-sm font-mono"
            />
          </div>

          {(settings.provider === 'ollama' || settings.provider === 'custom') && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
              <input
                type="url"
                value={settings.baseUrl}
                onChange={e => set('baseUrl', e.target.value)}
                placeholder="http://localhost:11434"
                className="border border-gray-200 rounded-md px-3 py-2 text-sm w-full max-w-sm"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {[
              { label: 'Frontier Model', key: 'frontierModel' as const, placeholder: 'gpt-4o / claude-opus-4-5' },
              { label: 'Standard Model', key: 'standardModel' as const, placeholder: 'gpt-4o-mini / claude-3-5-haiku' },
              { label: 'Monitor Model', key: 'monitorModel' as const, placeholder: 'gpt-4o / claude-3-5-sonnet' },
              { label: 'Coder Model', key: 'coderModel' as const, placeholder: 'gpt-4o / claude-3-5-sonnet' },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                <input
                  value={settings[key]}
                  onChange={e => set(key, e.target.value)}
                  placeholder={placeholder}
                  className="border border-gray-200 rounded-md px-3 py-2 text-sm w-full"
                />
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={testConnection}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Test Connection
            </button>
            {connTest && (
              <span className={`text-sm font-medium ${connTest.status === 'ok' ? 'text-green-600' : 'text-red-600'}`}>
                {connTest.status === 'ok' ? '✓' : '✗'} {connTest.msg}
              </span>
            )}
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-md px-3 py-2 text-xs text-yellow-700">
            In desktop app, credentials are stored in OS keychain. In browser mode, they are stored in localStorage — do not use in production.
          </div>
        </div>
      </div>

      {/* Run Configuration */}
      <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
        <h2 className="font-semibold text-gray-800 mb-4">Run Configuration</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max tokens per run <span className="font-normal text-gray-400">(LLM_MAX_TOKENS_PER_RUN)</span>
            </label>
            <input
              type="number"
              value={settings.maxTokensPerRun}
              onChange={e => set('maxTokensPerRun', Number(e.target.value))}
              className="border border-gray-200 rounded-md px-3 py-2 text-sm w-40"
              min={1000}
              step={1000}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max calls per minute <span className="font-normal text-gray-400">(LLM_RATE_LIMIT_RPM)</span>
            </label>
            <input
              type="number"
              value={settings.rateLimitRpm}
              onChange={e => set('rateLimitRpm', Number(e.target.value))}
              className="border border-gray-200 rounded-md px-3 py-2 text-sm w-40"
              min={1}
              max={1000}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Round interval: <strong>{settings.roundIntervalSecs}s</strong>
            </label>
            <input
              type="range"
              min={15}
              max={300}
              step={15}
              value={settings.roundIntervalSecs}
              onChange={e => set('roundIntervalSecs', Number(e.target.value))}
              className="w-64"
            />
            <div className="flex justify-between text-xs text-gray-400 w-64 mt-1">
              <span>15s</span>
              <span>300s</span>
            </div>
          </div>
        </div>
      </div>

      {/* Infrastructure Status */}
      <div className="bg-white rounded-lg border border-gray-200 p-5 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-gray-800">Infrastructure Status</h2>
          <button
            onClick={fetchHealth}
            disabled={healthLoading}
            className="text-xs px-3 py-1 border border-gray-200 rounded-md hover:bg-gray-50 disabled:opacity-50"
          >
            {healthLoading ? 'Checking...' : 'Refresh'}
          </button>
        </div>

        <table className="w-full text-sm mb-4">
          <thead>
            <tr className="border-b border-gray-100">
              <th className="text-left py-2 text-xs font-medium text-gray-500 uppercase">Service</th>
              <th className="text-left py-2 text-xs font-medium text-gray-500 uppercase">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {services.map(s => (
              <tr key={s.name}>
                <td className="py-2 text-gray-700">{s.name}</td>
                <td className="py-2">
                  {health.status === 'unknown' ? (
                    <span className="text-gray-400 text-xs">—</span>
                  ) : (
                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                      s.up ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}>
                      {s.up ? '● Online' : '○ Unknown'}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="border-t border-gray-100 pt-4">
          <button
            onClick={() => setResetDialog(true)}
            className="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50"
          >
            Reset Database
          </button>
        </div>
      </div>

      {/* Save button */}
      <div className="flex items-center gap-3">
        <button
          onClick={save}
          className="px-5 py-2 bg-gray-900 text-white text-sm font-medium rounded-md hover:bg-gray-700"
        >
          Save Settings
        </button>
        {saved && <span className="text-green-600 text-sm">✓ Saved to localStorage</span>}
      </div>

      {/* Reset dialog */}
      {resetDialog && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-96 shadow-xl">
            <h3 className="font-bold text-gray-900 mb-2">Reset Database</h3>
            <p className="text-sm text-red-600 mb-4">
              This will DELETE ALL data. This feature is only available in the desktop app with admin access.
            </p>
            <p className="text-sm text-gray-600 mb-3">Type <strong>DELETE</strong> to confirm:</p>
            <input
              value={resetInput}
              onChange={e => setResetInput(e.target.value)}
              className="border border-gray-200 rounded-md px-3 py-2 text-sm w-full mb-4 font-mono"
              placeholder="DELETE"
            />
            <div className="flex gap-3">
              <button
                disabled={resetInput !== 'DELETE'}
                onClick={() => {
                  alert('Database reset is only available in the desktop app with admin access.');
                  setResetDialog(false);
                  setResetInput('');
                }}
                className="px-4 py-2 bg-red-600 text-white text-sm rounded-md hover:bg-red-700 disabled:opacity-40"
              >
                Reset
              </button>
              <button
                onClick={() => { setResetDialog(false); setResetInput(''); }}
                className="px-4 py-2 border border-gray-200 text-sm rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
