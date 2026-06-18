'use client';

import { useEffect, useState } from 'react';

type Step = 'welcome' | 'docker' | 'ollama' | 'model' | 'starting' | 'done';

interface CheckState {
  docker: boolean | null;
  ollama: boolean | null;
  model: string;
  startupLog: string[];
}

declare global {
  interface Window {
    __TAURI__?: {
      invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
      event: {
        listen: (event: string, cb: (e: { payload: unknown }) => void) => Promise<() => void>;
      };
    };
  }
}

const isTauri = () => typeof window !== 'undefined' && !!window.__TAURI__;

function invoke<T = unknown>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri()) return Promise.resolve(null as T);
  return window.__TAURI__!.invoke(cmd, args) as Promise<T>;
}

export default function WizardPage() {
  const [step, setStep] = useState<Step>('welcome');
  const [state, setState] = useState<CheckState>({
    docker: null,
    ollama: null,
    model: 'qwen2.5:7b',
    startupLog: [],
  });
  const [pullProgress, setPullProgress] = useState<string>('');
  const [error, setError] = useState<string>('');

  const PLATFORM_DOCKER_URL =
    typeof navigator !== 'undefined' && navigator.platform.includes('Mac')
      ? 'https://docs.docker.com/desktop/install/mac-install/'
      : typeof navigator !== 'undefined' && navigator.platform.includes('Win')
      ? 'https://docs.docker.com/desktop/install/windows-install/'
      : 'https://docs.docker.com/desktop/install/linux-install/';

  async function checkDocker() {
    const ok = await invoke<boolean>('check_docker');
    setState(s => ({ ...s, docker: ok ?? false }));
    return ok;
  }

  async function checkOllama() {
    const ok = await invoke<boolean>('check_ollama');
    setState(s => ({ ...s, ollama: ok ?? false }));
    return ok;
  }

  async function startInfra() {
    setStep('starting');

    // Listen to startup events from Rust
    if (isTauri()) {
      await window.__TAURI__!.event.listen('startup', (e) => {
        const msg = e.payload as string;
        setState(s => ({ ...s, startupLog: [...s.startupLog, msg] }));
        if (msg === 'ready') {
          setTimeout(() => setStep('done'), 800);
        }
      });
      await window.__TAURI__!.event.listen('startup_error', (e) => {
        setError(e.payload as string);
      });
    } else {
      // Browser/dev mode: just check if backend is up
      setState(s => ({ ...s, startupLog: ['Checking backend...'] }));
      try {
        const r = await fetch('http://localhost:3001/health');
        if (r.ok) {
          setState(s => ({ ...s, startupLog: [...s.startupLog, 'Backend ready'] }));
          setTimeout(() => setStep('done'), 500);
        } else {
          setError('Backend not reachable — start it with: cd backend && npm run dev');
        }
      } catch {
        setError('Backend not reachable — start it with: cd backend && npm run dev');
      }
    }
  }

  async function pullModel() {
    setPullProgress('Pulling model...');
    try {
      await invoke('pull_model', { model: state.model });
      setPullProgress('Model ready ✓');
    } catch (e) {
      setPullProgress(`Error: ${e}`);
    }
  }

  const STEPS: Step[] = ['welcome', 'docker', 'ollama', 'model', 'starting', 'done'];
  const stepIdx = STEPS.indexOf(step);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm w-full max-w-lg">
        {/* Progress bar */}
        <div className="h-1 bg-gray-100 rounded-t-xl overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-500"
            style={{ width: `${((stepIdx + 1) / STEPS.length) * 100}%` }}
          />
        </div>

        <div className="p-8">
          {step === 'welcome' && (
            <div className="space-y-4">
              <h1 className="text-2xl font-bold text-gray-900">Welcome to AgentCo</h1>
              <p className="text-gray-600 text-sm leading-relaxed">
                AgentCo is an epistemic AI governance system. It runs 29 AI agents that
                make falsifiable predictions before acting, track their accuracy over time,
                and earn credibility only through verified outcomes — not self-assessment.
              </p>
              <p className="text-gray-500 text-sm">
                This wizard will set up everything you need. It takes about 2 minutes.
              </p>
              <button
                onClick={() => setStep('docker')}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700"
              >
                Get Started →
              </button>
            </div>
          )}

          {step === 'docker' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900">Step 1: Docker Desktop</h2>
              <p className="text-gray-600 text-sm">
                AgentCo uses Docker to run Postgres, Kafka, and Redis locally.
                Docker Desktop must be running.
              </p>
              <button
                onClick={checkDocker}
                className="w-full border border-gray-200 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50"
              >
                Check Docker
              </button>
              {state.docker === true && (
                <div className="flex items-center gap-2 text-green-700 text-sm bg-green-50 p-3 rounded-lg">
                  <span className="text-green-500">✓</span> Docker Desktop is running
                </div>
              )}
              {state.docker === false && (
                <div className="space-y-3">
                  <div className="text-red-700 text-sm bg-red-50 p-3 rounded-lg">
                    Docker Desktop is not running or not installed.
                  </div>
                  <a
                    href={PLATFORM_DOCKER_URL}
                    target="_blank"
                    rel="noreferrer"
                    className="block w-full text-center bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700"
                  >
                    Download Docker Desktop →
                  </a>
                  <p className="text-xs text-gray-400 text-center">
                    After installing, launch Docker Desktop and click Check Docker again.
                  </p>
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button onClick={() => setStep('welcome')} className="flex-1 text-gray-500 text-sm hover:text-gray-700">← Back</button>
                {state.docker !== false && (
                  <button
                    onClick={() => setStep('ollama')}
                    className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700"
                  >
                    Continue →
                  </button>
                )}
              </div>
            </div>
          )}

          {step === 'ollama' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900">Step 2: Ollama (Local AI)</h2>
              <p className="text-gray-600 text-sm">
                AgentCo uses Ollama to run AI models locally — no data leaves your machine,
                no API key needed by default.
              </p>
              <button
                onClick={checkOllama}
                className="w-full border border-gray-200 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50"
              >
                Check Ollama
              </button>
              {state.ollama === true && (
                <div className="flex items-center gap-2 text-green-700 text-sm bg-green-50 p-3 rounded-lg">
                  <span className="text-green-500">✓</span> Ollama is installed
                </div>
              )}
              {state.ollama === false && (
                <div className="space-y-3">
                  <div className="text-red-700 text-sm bg-red-50 p-3 rounded-lg">
                    Ollama is not installed.
                  </div>
                  <a
                    href="https://ollama.com/download"
                    target="_blank"
                    rel="noreferrer"
                    className="block w-full text-center bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700"
                  >
                    Download Ollama →
                  </a>
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <button onClick={() => setStep('docker')} className="flex-1 text-gray-500 text-sm hover:text-gray-700">← Back</button>
                <button
                  onClick={() => setStep('model')}
                  className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Continue →
                </button>
              </div>
            </div>
          )}

          {step === 'model' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900">Step 3: Choose Model</h2>
              <p className="text-gray-600 text-sm">
                Select which AI model to use. <strong>qwen2.5:7b</strong> runs on most
                laptops with 8GB RAM. Larger models are more capable but need more RAM.
              </p>
              <select
                value={state.model}
                onChange={e => setState(s => ({ ...s, model: e.target.value }))}
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm"
              >
                <option value="qwen2.5:7b">qwen2.5:7b — 4.7GB (recommended)</option>
                <option value="qwen2.5:14b">qwen2.5:14b — 9GB (more capable)</option>
                <option value="phi4">phi4 — 9.1GB (Microsoft)</option>
                <option value="llama3.2">llama3.2:3b — 2GB (fastest)</option>
                <option value="custom">Custom model name</option>
              </select>
              {pullProgress && (
                <div className="text-sm bg-blue-50 text-blue-700 p-3 rounded-lg">
                  {pullProgress}
                </div>
              )}
              <button
                onClick={pullModel}
                className="w-full border border-blue-200 text-blue-600 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-50"
              >
                Pull Model Now (optional — skip to do this later)
              </button>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setStep('ollama')} className="flex-1 text-gray-500 text-sm hover:text-gray-700">← Back</button>
                <button
                  onClick={startInfra}
                  className="flex-1 bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700"
                >
                  Start AgentCo →
                </button>
              </div>
            </div>
          )}

          {step === 'starting' && (
            <div className="space-y-4">
              <h2 className="text-xl font-bold text-gray-900">Starting AgentCo...</h2>
              <div className="space-y-1.5 min-h-32">
                {state.startupLog.map((msg, i) => (
                  <div key={i} className="text-sm text-gray-600 flex items-center gap-2">
                    <span className="w-4 text-green-500">✓</span>
                    <span className="capitalize">{msg.replace(/_/g, ' ')}</span>
                  </div>
                ))}
                {!error && state.startupLog.length < 6 && (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <span className="animate-spin">⟳</span>
                    <span>Please wait...</span>
                  </div>
                )}
                {error && (
                  <div className="text-red-600 text-sm bg-red-50 p-3 rounded-lg">
                    {error}
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 'done' && (
            <div className="space-y-4 text-center">
              <div className="text-5xl">✓</div>
              <h2 className="text-2xl font-bold text-gray-900">AgentCo is running</h2>
              <p className="text-gray-600 text-sm">
                All services started. The system is ready to run autonomous tasks,
                register predictions, and build its epistemic track record.
              </p>
              <a
                href="/"
                className="block w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700"
              >
                Open Dashboard →
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
