import { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { fetchXtream, getStreamUrl, getCreds } from '../api/xtream';
import { ArrowLeft, Loader2, Download } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';
import { save } from '@tauri-apps/plugin-dialog';

export default function Player() {
  const { type, id } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(type === 'series');
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [seasons, setSeasons] = useState<number[]>([]);
  const [activeSeason, setActiveSeason] = useState<number>(1);
  const [activeUrl, setActiveUrl] = useState('');
  const [activeTitle, setActiveTitle] = useState('');
  const [activeEp, setActiveEp] = useState<any>(null);
  const [downloading, setDownloading] = useState<Record<string, boolean>>({});

  const item = state?.item;

  useEffect(() => {
    try { getCreds(); } catch { navigate('/'); return; }

    if (type === 'movie') {
      setActiveUrl(getStreamUrl('movie', id as string, item?.container_extension || 'mp4'));
      setActiveTitle(item?.name || 'Movie');
      setLoading(false);
    } else {
      loadSeriesInfo();
    }
  }, [type, id]);

  const loadSeriesInfo = async () => {
    try {
      const data = await fetchXtream('get_series_info', { series_id: id as string });
      const eps = data.episodes || {};
      const allEps: any[] = [];
      for (const season in eps) {
        allEps.push(...eps[season]);
      }
      const uniqueSeasons = [...new Set(allEps.map((e: any) => Number(e.season)))].sort((a, b) => a - b);
      setEpisodes(allEps);
      setSeasons(uniqueSeasons);
      if (uniqueSeasons.length > 0) setActiveSeason(uniqueSeasons[0]);
      if (allEps.length > 0) selectEpisode(allEps[0]);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const selectEpisode = (ep: any) => {
    setActiveUrl(getStreamUrl('series', ep.id, ep.container_extension || 'mp4'));
    setActiveTitle(ep.title || `Episode ${ep.episode_num}`);
    setActiveEp(ep);
  };

  const downloadFile = async (url: string, defaultFilename: string, id: string) => {
    if (downloading[id]) return;
    try {
      const path = await save({ defaultPath: defaultFilename });
      if (!path) return; // User canceled

      setDownloading(prev => ({ ...prev, [id]: true }));
      await invoke('download_file', { url, path });
      setDownloading(prev => ({ ...prev, [id]: false }));
      alert(`Download complete: ${defaultFilename}`);
    } catch (err: any) {
      alert(`Download failed: ${err}`);
      setDownloading(prev => ({ ...prev, [id]: false }));
    }
  };



  const seasonEps = episodes.filter(e => Number(e.season) === activeSeason);

  return (
    <div className="min-h-screen bg-black flex flex-col">
      {/* Header */}
      <header className="glass px-4 py-3 flex items-center justify-between z-10 border-b border-white/5">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-white/10 rounded-full transition-colors text-white">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-base font-bold leading-tight" dir="auto">{item?.name || 'Video Player'}</h1>
            <p className="text-xs text-[#00f3ff] font-mono opacity-80">{activeTitle}</p>
          </div>
        </div>

        <div className="flex gap-2">
          {type === 'movie' ? (
            <button
              onClick={() => downloadFile(activeUrl, `${item?.name || 'movie'}.${item?.container_extension || 'mp4'}`, 'movie')}
              disabled={downloading['movie']}
              className="flex items-center gap-2 px-3 py-2 bg-[#00f3ff]/10 text-[#00f3ff] border border-[#00f3ff]/30 hover:bg-[#00f3ff]/20 rounded-lg font-mono text-xs uppercase tracking-wider transition-colors disabled:opacity-50"
            >
              {downloading['movie'] ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} 
              {downloading['movie'] ? 'Downloading' : 'Download'}
            </button>
          ) : (
            <>
              <button
                onClick={() => activeEp && downloadFile(activeUrl, `${item?.name} S${String(activeEp.season).padStart(2,'0')}E${String(activeEp.episode_num).padStart(2,'0')}.${activeEp.container_extension || 'mp4'}`, activeEp.id)}
                disabled={!activeEp || downloading[activeEp.id]}
                className="flex items-center gap-2 px-3 py-2 bg-[#00f3ff]/10 text-[#00f3ff] border border-[#00f3ff]/30 hover:bg-[#00f3ff]/20 rounded-lg font-mono text-xs uppercase tracking-wider transition-colors disabled:opacity-50"
              >
                {activeEp && downloading[activeEp.id] ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} 
                {activeEp && downloading[activeEp.id] ? 'Downloading' : 'Episode'}
              </button>
              {/* <button
                onClick={downloadSeason}
                className="flex items-center gap-2 px-3 py-2 bg-[#bc13fe]/10 text-[#bc13fe] border border-[#bc13fe]/30 hover:bg-[#bc13fe]/20 rounded-lg font-mono text-xs uppercase tracking-wider transition-colors"
              >
                <FolderDown size={14} /> Season {activeSeason}
              </button> */}
            </>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 56px)' }}>
        {/* Video */}
        <main className="flex-1 bg-black flex items-center justify-center">
          {loading ? (
            <Loader2 className="w-12 h-12 text-[#00f3ff] animate-spin" />
          ) : activeUrl ? (
            <video
              key={activeUrl}
              src={activeUrl}
              controls
              autoPlay
              className="w-full h-full object-contain"
            >
              Your browser does not support the video tag.
            </video>
          ) : (
            <p className="text-gray-500 font-mono">No video source.</p>
          )}
        </main>

        {/* Episodes panel */}
        {type === 'series' && episodes.length > 0 && (
          <aside className="w-80 glass border-l border-white/5 flex flex-col overflow-hidden">
            {/* Season tabs */}
            {seasons.length > 1 && (
              <div className="flex gap-1 p-3 border-b border-white/5 flex-wrap">
                {seasons.map(s => (
                  <button
                    key={s}
                    onClick={() => setActiveSeason(s)}
                    className={`px-3 py-1 rounded-full text-xs font-mono transition-all ${
                      activeSeason === s
                        ? 'bg-[#00f3ff]/20 text-[#00f3ff] border border-[#00f3ff]/40'
                        : 'text-gray-500 hover:text-white border border-white/10 hover:border-white/20'
                    }`}
                  >
                    S{s}
                  </button>
                ))}
              </div>
            )}

            <div className="overflow-y-auto flex-1 p-3 space-y-2">
              <h3 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-2">
                Season {activeSeason} — {seasonEps.length} episodes
              </h3>
              {seasonEps.map(ep => {
                const isPlaying = activeEp?.id === ep.id;
                return (
                  <button
                    key={ep.id}
                    onClick={() => selectEpisode(ep)}
                    className={`w-full text-left p-3 rounded-xl flex gap-3 transition-colors ${
                      isPlaying
                        ? 'bg-[#00f3ff]/15 border border-[#00f3ff]/40'
                        : 'bg-[#111] hover:bg-[#1a1a1a] border border-white/5'
                    }`}
                  >
                    <img
                      src={ep.info?.movie_image || item?.cover || item?.stream_icon || ''}
                      alt=""
                      className="w-20 h-12 object-cover rounded bg-[#222] flex-shrink-0"
                      onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
                    />
                    <div className="flex-1 overflow-hidden">
                      <p className="text-xs text-[#00f3ff] font-mono mb-0.5">E{ep.episode_num}</p>
                      <h4 className="text-sm font-medium truncate text-white leading-tight" dir="auto">
                        {ep.title || `Episode ${ep.episode_num}`}
                      </h4>
                    </div>
                  </button>
                );
              })}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
