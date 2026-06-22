import { useNavigate } from 'react-router-dom';
import { Zap, ArrowLeft, Download, Settings as SettingsIcon } from 'lucide-react';

export default function Header() {
  const navigate = useNavigate();
  
  return (
    <header className="sticky top-0 z-50 glass px-6 py-3 flex items-center justify-between border-b border-white/5 bg-black/80">
      <div className="flex items-center gap-6">
        <button onClick={() => navigate('/browse')} className="p-2 hover:bg-white/10 rounded-full transition-colors text-white">
          <ArrowLeft size={20} />
        </button>
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => navigate('/browse')}>
          <Zap className="w-5 h-5 text-[#00f3ff]" strokeWidth={1.5} />
          <span className="text-lg font-black tracking-widest uppercase font-mono">
            Xtream<span className="text-[#00f3ff]">Rip</span>
          </span>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/downloads')}
          className="flex items-center gap-2 text-gray-400 hover:text-[#00f3ff] transition-colors p-2 rounded-full hover:bg-[#00f3ff]/10"
          title="Downloads"
        >
          <Download size={18} />
          <span className="text-sm font-mono uppercase">Queue</span>
        </button>
        <button
          onClick={() => navigate('/settings')}
          className="flex items-center gap-2 text-gray-400 hover:text-[#bc13fe] transition-colors p-2 rounded-full hover:bg-[#bc13fe]/10"
          title="Settings"
        >
          <SettingsIcon size={18} />
          <span className="text-sm font-mono uppercase">Settings</span>
        </button>
      </div>
    </header>
  );
}
