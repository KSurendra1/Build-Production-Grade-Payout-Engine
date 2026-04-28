import { Activity, Zap } from 'lucide-react';

export default function Layout({ children }) {
  return (
    <div className="min-h-screen bg-dark-900 font-sans text-gray-100 relative overflow-hidden">
      {/* Animated Background Blobs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-brand-600/20 rounded-full mix-blend-screen filter blur-[100px] animate-blob"></div>
      <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-purple-600/20 rounded-full mix-blend-screen filter blur-[100px] animate-blob" style={{ animationDelay: '2s' }}></div>
      <div className="absolute -bottom-32 left-1/2 w-[500px] h-[500px] bg-emerald-600/10 rounded-full mix-blend-screen filter blur-[120px] animate-blob" style={{ animationDelay: '4s' }}></div>

      {/* Header */}
      <header className="relative z-10 glass-panel border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-3 group cursor-pointer">
              <div className="p-2 bg-brand-500/20 rounded-xl border border-brand-500/30 group-hover:bg-brand-500/30 transition-colors">
                <Zap className="h-6 w-6 text-brand-400 group-hover:text-brand-300 drop-shadow-[0_0_15px_rgba(104,117,245,0.5)]" />
              </div>
              <h1 className="text-2xl font-bold text-white tracking-tight">
                Playto<span className="text-brand-400">Engine</span>
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              <div className="hidden md:flex items-center px-4 py-2 bg-dark-800/50 rounded-full border border-white/5">
                <div className="w-2 h-2 rounded-full bg-emerald-400 mr-2 animate-pulse-slow shadow-[0_0_10px_rgba(52,211,153,0.5)]"></div>
                <span className="text-sm font-medium text-gray-300">Live API Connected</span>
              </div>
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-brand-500 to-purple-500 p-[2px]">
                <div className="w-full h-full bg-dark-900 rounded-full flex items-center justify-center">
                  <span className="text-sm font-bold text-white">TC</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 animate-fade-in">
        {children}
      </main>
    </div>
  );
}
