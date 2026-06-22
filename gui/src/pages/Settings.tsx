import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { Save, FolderSearch } from 'lucide-react';
import { open } from '@tauri-apps/plugin-dialog';
import Header from '../components/Header';

export default function Settings() {
  const [workers, setWorkers] = useState<number>(1);
  const [downloadDir, setDownloadDir] = useState<string>('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    invoke('get_settings').then((s: any) => {
      if (s) {
        setWorkers(s.workers);
        setDownloadDir(s.download_dir);
      }
    }).catch(console.error);
  }, []);

  const selectDir = async () => {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        defaultPath: downloadDir || undefined,
      });
      if (selected && typeof selected === 'string') {
        setDownloadDir(selected);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const saveSettings = async () => {
    setSaving(true);
    try {
      await invoke('set_settings', { settings: { workers: Number(workers), download_dir: downloadDir } });
      alert("Settings saved! Note: Changes to worker count may require restarting the app.");
    } catch (err) {
      alert(`Failed to save settings: ${err}`);
    }
    setSaving(false);
  };

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <Header />
      
      <main className="flex-1 max-w-3xl w-full mx-auto p-6 mt-10">
        <h1 className="text-3xl font-bold mb-8 font-mono uppercase tracking-wider text-[#00f3ff]">Settings</h1>
        
        <div className="glass p-8 rounded-2xl border border-white/10 space-y-8">
          
          <div>
            <label className="block text-sm font-mono text-[#00f3ff] mb-2 uppercase tracking-wide">
              Max Concurrent Workers
            </label>
            <p className="text-xs text-gray-500 mb-3">
              How many downloads to run at the exact same time. Set this to 1 to avoid IPTV server blocks.
            </p>
            <input 
              type="number" 
              min="1" 
              max="10"
              value={workers}
              onChange={(e) => setWorkers(parseInt(e.target.value) || 1)}
              className="w-full bg-[#111] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-[#00f3ff] font-mono"
            />
          </div>

          <div>
            <label className="block text-sm font-mono text-[#00f3ff] mb-2 uppercase tracking-wide">
              Default Download Directory
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Where to save your movies and series. Leave empty to use your default Downloads/XtreamRip folder.
            </p>
            <div className="flex gap-3">
              <input 
                type="text" 
                value={downloadDir}
                onChange={(e) => setDownloadDir(e.target.value)}
                placeholder="e.g. C:\Downloads\XtreamRip"
                className="flex-1 bg-[#111] border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-[#00f3ff] font-mono"
              />
              <button 
                onClick={selectDir}
                className="px-4 py-3 bg-[#111] hover:bg-[#222] border border-white/10 rounded-xl transition-colors"
              >
                <FolderSearch size={20} />
              </button>
            </div>
          </div>

          <button 
            onClick={saveSettings}
            disabled={saving}
            className="w-full mt-4 flex items-center justify-center gap-2 bg-[#00f3ff]/10 text-[#00f3ff] border border-[#00f3ff]/30 hover:bg-[#00f3ff]/20 px-6 py-4 rounded-xl font-mono uppercase tracking-wider transition-colors disabled:opacity-50"
          >
            <Save size={18} />
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </main>
    </div>
  );
}
