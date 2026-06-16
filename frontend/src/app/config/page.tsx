'use client';

export default function ConfigPage() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900">Config Change History</h1>
      <p className="text-gray-500 mt-1">Full version history of all agent prompts with diff view and one-click rollback</p>
      <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm text-yellow-800">
        ⚠️ All prompt changes require human approval. Config-Agent cannot act without an approval token.
      </div>
      <div className="mt-6 bg-white rounded-lg border border-gray-200 p-4">
        <p className="text-gray-400 text-sm text-center py-8">
          Prompt version history will appear here. All changes are logged in the prompt_registry table.
        </p>
      </div>
    </div>
  );
}
