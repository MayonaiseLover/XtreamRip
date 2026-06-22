import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Zap, Globe, User, Lock, Eye, EyeOff } from 'lucide-react';
import { saveCreds, fetchXtream, clearCreds } from '../api/xtream';

export default function Login() {
  const [url, setUrl] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    // Normalize URL
    let base = url.trim().replace(/\/$/, '');
    if (!base.startsWith('http')) base = 'http://' + base;

    saveCreds({ baseUrl: base, username: username.trim(), password: password.trim() });

    try {
      // Validate credentials by calling get_series_categories
      await fetchXtream('get_series_categories');
      navigate('/browse');
    } catch (err: any) {
      clearCreds();
      setError('Connection failed. Check your Server URL, username, and password.');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a] relative overflow-hidden">
      {/* Animated background */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(0,243,255,0.12),transparent)]" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_40%_40%_at_80%_80%,rgba(188,19,254,0.08),transparent)]" />
      
      {/* Grid lines */}
      <div className="absolute inset-0 opacity-[0.03]"
        style={{ backgroundImage: 'linear-gradient(#00f3ff 1px, transparent 1px), linear-gradient(90deg, #00f3ff 1px, transparent 1px)', backgroundSize: '60px 60px' }} 
      />

      <div className="relative w-full max-w-md mx-4">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="relative mb-4">
            <div className="absolute inset-0 bg-[#00f3ff] blur-2xl opacity-20 rounded-full" />
            <div className="relative p-4 bg-black/60 rounded-2xl border border-[#00f3ff]/30 shadow-[0_0_30px_rgba(0,243,255,0.15)]">
              <Zap className="w-12 h-12 text-[#00f3ff]" strokeWidth={1.5} />
            </div>
          </div>
          <h1 className="text-3xl font-black tracking-[0.2em] uppercase font-mono text-white">
            Xtream<span className="text-[#00f3ff]">Rip</span>
          </h1>
          <p className="text-xs text-gray-500 font-mono mt-2 tracking-widest uppercase">
            IPTV Browser &amp; Downloader
          </p>
        </div>

        {/* Card */}
        <div className="glass p-8 rounded-2xl border border-white/8 shadow-[0_0_60px_rgba(0,0,0,0.5)]">
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Server URL */}
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-gray-400 uppercase tracking-widest flex items-center gap-2">
                <Globe size={12} className="text-[#00f3ff]" /> Server URL
              </label>
              <input
                type="text"
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="http://yourserver.com:8080"
                required
                className="w-full bg-black/60 border border-white/10 focus:border-[#00f3ff]/60 rounded-lg px-4 py-3 text-sm font-mono outline-none transition-all placeholder-gray-600 text-white focus:shadow-[0_0_15px_rgba(0,243,255,0.1)]"
              />
            </div>

            {/* Username */}
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-gray-400 uppercase tracking-widest flex items-center gap-2">
                <User size={12} className="text-[#00f3ff]" /> Username
              </label>
              <input
                type="text"
                value={username}
                onChange={e => setUsername(e.target.value)}
                placeholder="your_username"
                required
                className="w-full bg-black/60 border border-white/10 focus:border-[#00f3ff]/60 rounded-lg px-4 py-3 text-sm font-mono outline-none transition-all placeholder-gray-600 text-white focus:shadow-[0_0_15px_rgba(0,243,255,0.1)]"
              />
            </div>

            {/* Password */}
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-gray-400 uppercase tracking-widest flex items-center gap-2">
                <Lock size={12} className="text-[#00f3ff]" /> Password
              </label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="your_password"
                  required
                  className="w-full bg-black/60 border border-white/10 focus:border-[#00f3ff]/60 rounded-lg px-4 py-3 pr-12 text-sm font-mono outline-none transition-all placeholder-gray-600 text-white focus:shadow-[0_0_15px_rgba(0,243,255,0.1)]"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-[#00f3ff] transition-colors"
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm font-mono flex items-start gap-2">
                <span className="w-1.5 h-1.5 bg-red-500 rounded-full mt-1.5 flex-shrink-0 animate-pulse" />
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full mt-2 py-3.5 bg-gradient-to-r from-[#00f3ff]/20 to-[#bc13fe]/20 hover:from-[#00f3ff]/30 hover:to-[#bc13fe]/30 border border-[#00f3ff]/40 text-white font-mono uppercase tracking-[0.2em] text-sm rounded-lg transition-all hover:shadow-[0_0_25px_rgba(0,243,255,0.2)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-[#00f3ff]/40 border-t-[#00f3ff] rounded-full animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <Zap size={16} className="text-[#00f3ff]" />
                  Connect
                </>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-gray-600 text-xs font-mono mt-6">
          Your credentials are stored locally on this device only.
        </p>
      </div>
    </div>
  );
}
