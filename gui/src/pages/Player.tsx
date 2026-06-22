import { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { fetchXtream, getStreamUrl, getCreds } from '../api/xtream';
import { ArrowLeft, Loader2, Download, FolderDown, Info } from 'lucide-react';
import { invoke } from '@tauri-apps/api/core';

export default function Player() {
  const { type, id } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();
  const [, setLoading] = useState(type === 'series');
  const [episodes, setEpisodes] = useState<any[]>([]);
  const [seasons, setSeasons] = useState<number[]>([]);
  const [activeSeason, setActiveSeason] = useState<number>(1);
  const [activeUrl, setActiveUrl] = useState('');
  const [, setActiveTitle] = useState('');
  const [activeEp, setActiveEp] = useState<any>(null);
  const [downloading, setDownloading] = useState<Record<string, boolean>>({});
  const [appSettings, setAppSettings] = useState<any>(null);

  const item = state?.item;

  useEffect(() => {
    try { getCreds(); } catch { navigate('/'); return; }
    
    invoke('get_settings').then((s: any) => setAppSettings(s)).catch(console.error);

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

  const sanitizeFilename = (name: string) => {
    return name.replace(/[\\/:*?"<>|]/g, '-').trim();
  };

  const getDestPath = (ep: any | null = null) => {
    const baseDir = appSettings?.download_dir || '';
    if (type === 'movie') {
      const movieName = sanitizeFilename(item?.name || 'Unknown Movie');
      const ext = item?.container_extension || 'mp4';
      return `${baseDir}\\movies\\${movieName}\\${movieName}.${ext}`;
    } else {
      const seriesName = sanitizeFilename(item?.name || 'Unknown Series');
      const ext = ep?.container_extension || 'mp4';
      const seasonNum = Number(ep?.season);
      const epNum = Number(ep?.episode_num);
      const epTitle = sanitizeFilename(ep?.title || `Episode ${epNum}`);
      const filename = `S${String(seasonNum).padStart(2,'0')}E${String(epNum).padStart(2,'0')} - ${epTitle}.${ext}`;
      
      if (seasons.length > 1) {
        return `${baseDir}\\series\\${seriesName}\\Season ${seasonNum}\\${filename}`;
      } else {
        return `${baseDir}\\series\\${seriesName}\\${filename}`;
      }
    }
  };

  const downloadItem = async (url: string, path: string, displayName: string, trackId: string) => {
    if (downloading[trackId]) return;
    setDownloading(prev => ({ ...prev, [trackId]: true }));
    try {
      await invoke('add_to_queue', { url, dest: path, name: displayName });
    } catch (err: any) {
      alert(`Failed to add to queue: ${err}`);
    }
    // We keep the "Downloading" state true for UI feedback, the Downloads tab handles the rest
  };

  const downloadActiveMovie = () => {
    const path = getDestPath();
    downloadItem(activeUrl, path, item?.name || 'Movie', 'movie');
  };

  const downloadActiveEpisode = () => {
    if (!activeEp) return;
    const path = getDestPath(activeEp);
    downloadItem(activeUrl, path, `${item?.name} S${activeEp.season}E${activeEp.episode_num}`, activeEp.id);
  };

  const downloadSeason = () => {
    const eps = episodes.filter(e => Number(e.season) === activeSeason);
    eps.forEach(ep => {
      const url = getStreamUrl('series', ep.id, ep.container_extension || 'mp4');
      const path = getDestPath(ep);
      downloadItem(url, path, `${item?.name} S${ep.season}E${ep.episode_num}`, ep.id);
    });
  };

  const seasonEps = episodes.filter(e => Number(e.season) === activeSeason);

  return (
    <div className="min-h-screen bg-black flex flex-col">
      <header className="glass px-4 py-3 flex items-center justify-between z-10 border-b border-white/5">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-white/10 rounded-full transition-colors text-white">
            <ArrowLeft size={20} />
          </button>
          <div>
            <h1 className="text-base font-bold leading-tight" dir="auto">{item?.name || 'Media Info'}</h1>
            <p className="text-xs text-[#00f3ff] font-mono opacity-80">{type === 'series' ? 'Series' : 'Movie'}</p>
          </div>
        </div>

        <div className="flex gap-2">
          {type === 'movie' ? (
            <button
              onClick={downloadActiveMovie}
              disabled={downloading['movie']}
              className="flex items-center gap-2 px-3 py-2 bg-[#00f3ff]/10 text-[#00f3ff] border border-[#00f3ff]/30 hover:bg-[#00f3ff]/20 rounded-lg font-mono text-xs uppercase tracking-wider transition-colors disabled:opacity-50"
            >
              {downloading['movie'] ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} 
              {downloading['movie'] ? 'Queued' : 'Download Movie'}
            </button>
          ) : (
            <>
              <button
                onClick={downloadActiveEpisode}
                disabled={!activeEp || downloading[activeEp.id]}
                className="flex items-center gap-2 px-3 py-2 bg-[#00f3ff]/10 text-[#00f3ff] border border-[#00f3ff]/30 hover:bg-[#00f3ff]/20 rounded-lg font-mono text-xs uppercase tracking-wider transition-colors disabled:opacity-50"
              >
                {activeEp && downloading[activeEp.id] ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} 
                {activeEp && downloading[activeEp.id] ? 'Queued' : 'Download Ep'}
              </button>
              <button
                onClick={downloadSeason}
                className="flex items-center gap-2 px-3 py-2 bg-[#bc13fe]/10 text-[#bc13fe] border border-[#bc13fe]/30 hover:bg-[#bc13fe]/20 rounded-lg font-mono text-xs uppercase tracking-wider transition-colors"
              >
                <FolderDown size={14} /> Download S{activeSeason}
              </button>
            </>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 56px)' }}>
        {/* Info Panel instead of Video Player */}
        <main className="flex-1 bg-black flex flex-col items-center justify-center p-8 relative">
          <div className="absolute inset-0 opacity-20 pointer-events-none" style={{
            backgroundImage: `url(${item?.stream_icon || item?.cover || ''})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            filter: 'blur(40px)'
          }} />
          
          <div className="z-10 flex flex-col items-center max-w-2xl text-center">
            {item?.stream_icon || item?.cover ? (
              <img 
                src={item.stream_icon || item.cover} 
                className="w-64 rounded-xl shadow-2xl mb-8 border border-white/10"
                alt="Poster" 
              />
            ) : (
              <div className="w-64 h-96 bg-[#111] rounded-xl flex items-center justify-center mb-8 border border-white/5">
                <Info size={48} className="text-white/20" />
              </div>
            )}
            
            <h2 className="text-3xl font-bold text-white mb-2">{item?.name}</h2>
            
            {type === 'movie' && (
              <div className="flex gap-4 text-sm font-mono text-gray-400 mt-2">
                <span>Rating: {item?.rating || 'N/A'}</span>
                <span>Year: {item?.year || 'N/A'}</span>
              </div>
            )}
            
            {type === 'series' && activeEp && (
              <div className="mt-6 p-6 bg-white/5 backdrop-blur-xl rounded-2xl border border-white/10 text-left w-full">
                <h3 className="text-lg font-bold text-[#00f3ff] mb-1">
                  Season {activeEp.season} Episode {activeEp.episode_num}
                </h3>
                <h4 className="text-xl text-white mb-2">{activeEp.title || `Episode ${activeEp.episode_num}`}</h4>
                <p className="text-gray-400 text-sm leading-relaxed">
                  {activeEp.info?.plot || activeEp.info?.description || "No episode description available."}
                </p>
              </div>
            )}
          </div>
        </main>

        {/* Episodes panel */}
        {type === 'series' && episodes.length > 0 && (
          <aside className="w-96 glass border-l border-white/5 flex flex-col overflow-hidden">
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
                const isSelected = activeEp?.id === ep.id;
                return (
                  <div
                    key={ep.id}
                    className={`w-full text-left p-3 rounded-xl flex gap-3 transition-colors cursor-pointer ${
                      isSelected
                        ? 'bg-[#00f3ff]/15 border border-[#00f3ff]/40'
                        : 'bg-[#111] hover:bg-[#1a1a1a] border border-white/5'
                    }`}
                    onClick={() => selectEpisode(ep)}
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
                  </div>
                );
              })}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}
