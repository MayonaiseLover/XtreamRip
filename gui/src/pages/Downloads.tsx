import { useEffect, useState } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';
import { Loader2, CheckCircle, XCircle, Clock } from 'lucide-react';
import Header from '../components/Header';

interface DownloadItem {
  id: string;
  url: string;
  dest: string;
  name: string;
  status: string;
  progress: number;
}

export default function Downloads() {
  const [queue, setQueue] = useState<DownloadItem[]>([]);

  const fetchQueue = async () => {
    try {
      const q: DownloadItem[] = await invoke('get_queue');
      setQueue(q.reverse()); // Show newest first
    } catch (err) {
      console.error('Failed to fetch queue', err);
    }
  };

  useEffect(() => {
    fetchQueue();
    const unlisten = listen('download-update', () => {
      fetchQueue();
    });

    return () => {
      unlisten.then(f => f());
    };
  }, []);

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      <Header />
      
      <main className="flex-1 max-w-5xl w-full mx-auto p-6 overflow-y-auto">
        <h1 className="text-2xl font-bold mb-6 font-mono uppercase tracking-wider text-[#00f3ff]">Download Queue</h1>
        
        {queue.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-gray-500 border border-white/5 rounded-2xl bg-white/5 border-dashed">
            <Clock size={48} className="mb-4 opacity-50" />
            <p className="font-mono">Queue is empty.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {queue.map(item => (
              <div key={item.id} className="glass p-4 rounded-xl border border-white/10 flex items-center gap-4">
                {item.status === 'Downloading' ? (
                  <Loader2 size={24} className="text-[#00f3ff] animate-spin" />
                ) : item.status === 'Done' ? (
                  <CheckCircle size={24} className="text-green-500" />
                ) : item.status.startsWith('Error') ? (
                  <XCircle size={24} className="text-red-500" />
                ) : (
                  <Clock size={24} className="text-gray-500" />
                )}
                
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium truncate text-sm mb-1">{item.name}</h3>
                  <p className="text-xs text-gray-500 font-mono truncate">{item.dest}</p>
                  
                  {item.status === 'Downloading' && (
                    <div className="mt-3 bg-black/50 rounded-full h-1.5 overflow-hidden border border-white/5">
                      <div 
                        className="bg-[#00f3ff] h-full transition-all duration-300 ease-out"
                        style={{ width: `${item.progress}%` }}
                      />
                    </div>
                  )}
                </div>
                
                <div className="text-right flex-shrink-0 w-24">
                  <p className="text-xs font-mono font-bold">
                    {item.status === 'Downloading' ? `${item.progress}%` : item.status === 'Done' ? 'Complete' : item.status.startsWith('Error') ? 'Failed' : 'Pending'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
