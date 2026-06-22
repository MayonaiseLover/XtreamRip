import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchXtream, getCreds, clearCreds } from '../api/xtream';
import { Play, LogOut, Clapperboard, Tv, Loader2, Zap } from 'lucide-react';

type Category = { category_id: string; category_name: string };
type MediaItem = {
  num: number;
  name: string;
  stream_id?: number;
  series_id?: number;
  cover?: string;
  stream_icon?: string;
  rating?: string;
  container_extension?: string;
};

function getPoster(item: MediaItem): string {
  return item.cover || item.stream_icon || '';
}

export default function Browse() {
  const navigate = useNavigate();
  const [type, setType] = useState<'movie' | 'series'>('series');
  const [categories, setCategories] = useState<Category[]>([]);
  const [activeCat, setActiveCat] = useState<string>('');
  const [items, setItems] = useState<MediaItem[]>([]);
  const [loadingCats, setLoadingCats] = useState(true);
  const [loadingItems, setLoadingItems] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    try {
      getCreds(); // throws if not set
    } catch {
      navigate('/');
      return;
    }
    loadCategories(type);
  }, [type]);

  const loadCategories = async (mediaType: 'movie' | 'series') => {
    setLoadingCats(true);
    setErrorMsg(null);
    setItems([]);
    try {
      const data = await fetchXtream(mediaType === 'movie' ? 'get_vod_categories' : 'get_series_categories');
      setCategories(data);
      if (data.length > 0) {
        setActiveCat(data[0].category_id);
        loadItems(mediaType, data[0].category_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load categories');
    }
    setLoadingCats(false);
  };

  const loadItems = async (mediaType: 'movie' | 'series', categoryId: string) => {
    setLoadingItems(true);
    setActiveCat(categoryId);
    setSearch('');
    try {
      const data = await fetchXtream(
        mediaType === 'movie' ? 'get_vod_streams' : 'get_series',
        { category_id: categoryId }
      );
      setItems(data);
    } catch (err) {
      console.error(err);
    }
    setLoadingItems(false);
  };

  const handleLogout = () => {
    clearCreds();
    navigate('/');
  };

  const openPlayer = (item: MediaItem) => {
    const id = item.stream_id || item.series_id;
    navigate(`/player/${type}/${id}`, { state: { item } });
  };

  const filtered = items.filter(i => i.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="min-h-screen flex flex-col">
      {/* Navbar */}
      <header className="sticky top-0 z-50 glass px-6 py-3 flex items-center justify-between border-b border-white/5">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Zap className="w-5 h-5 text-[#00f3ff]" strokeWidth={1.5} />
            <span className="text-lg font-black tracking-widest uppercase font-mono">
              Xtream<span className="text-[#00f3ff]">Rip</span>
            </span>
          </div>
          <nav className="flex gap-2">
            <button
              onClick={() => setType('series')}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                type === 'series'
                  ? 'bg-[#00f3ff]/20 text-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.2)]'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Tv size={15} /> Series
            </button>
            <button
              onClick={() => setType('movie')}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all ${
                type === 'movie'
                  ? 'bg-[#00f3ff]/20 text-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.2)]'
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Clapperboard size={15} /> Movies
            </button>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search..."
            className="bg-black/40 border border-white/10 rounded-full px-4 py-1.5 text-sm outline-none focus:border-[#00f3ff]/40 text-white placeholder-gray-600 w-48 transition-all focus:w-64"
          />
          <button
            onClick={handleLogout}
            className="text-gray-400 hover:text-red-400 transition-colors p-2 rounded-full hover:bg-red-400/10"
            title="Disconnect"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 56px)' }}>
        {/* Sidebar */}
        <aside className="w-60 glass border-r border-white/5 overflow-y-auto flex-shrink-0">
          <div className="p-3 space-y-0.5">
            <h2 className="text-xs font-mono text-gray-500 uppercase tracking-widest mb-3 px-2 pt-1">Genres</h2>
            {loadingCats ? (
              <div className="flex justify-center p-8 text-[#00f3ff]"><Loader2 className="animate-spin" /></div>
            ) : categories.map(cat => (
              <button
                key={cat.category_id}
                onClick={() => loadItems(type, cat.category_id)}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-all ${
                  activeCat === cat.category_id
                    ? 'bg-gradient-to-r from-[#00f3ff]/20 to-transparent text-white border-l-2 border-[#00f3ff]'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-white/5 border-l-2 border-transparent'
                }`}
              >
                {cat.category_name}
              </button>
            ))}
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#0a0a0a]">
          {errorMsg && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl mb-6">
              <h3 className="font-bold mb-1">Connection Error</h3>
              <p className="text-sm">{errorMsg}</p>
            </div>
          )}
          {loadingItems ? (
            <div className="flex justify-center items-center h-64 text-[#00f3ff]">
              <Loader2 className="w-10 h-10 animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 gap-5">
              {filtered.map(item => (
                <div
                  key={item.stream_id || item.series_id}
                  className="group relative rounded-xl overflow-hidden cursor-pointer transition-transform duration-300 hover:scale-105 hover:shadow-[0_0_30px_rgba(0,243,255,0.12)] ring-1 ring-white/5 hover:ring-[#00f3ff]/40 bg-[#111]"
                  onClick={() => openPlayer(item)}
                >
                  <div className="aspect-[2/3] relative">
                    {getPoster(item) ? (
                      <img
                        src={getPoster(item)}
                        alt={item.name}
                        className="w-full h-full object-cover transition-opacity duration-300 group-hover:opacity-50"
                        onError={e => { e.currentTarget.src = ''; e.currentTarget.style.display = 'none'; }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-[#1a1a1a] text-gray-600 font-mono text-xs p-2 text-center">
                        {item.name}
                      </div>
                    )}
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <div className="bg-[#00f3ff]/20 p-4 rounded-full backdrop-blur-md border border-[#00f3ff]/50">
                        <Play className="w-7 h-7 text-[#00f3ff] fill-[#00f3ff]" />
                      </div>
                    </div>
                  </div>
                  <div className="absolute bottom-0 w-full p-2.5 bg-gradient-to-t from-black via-black/80 to-transparent">
                    <h3 className="font-medium text-xs truncate leading-snug" dir="auto">{item.name}</h3>
                    {item.rating && item.rating !== '0' && (
                      <div className="flex items-center gap-1 mt-0.5 text-xs text-yellow-500">
                        <span>★</span> {parseFloat(item.rating).toFixed(1)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {!loadingItems && filtered.length === 0 && items.length > 0 && (
                <p className="col-span-full text-center text-gray-600 font-mono py-20">No results for "{search}"</p>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
