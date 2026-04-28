import { CreditCard, Clock } from 'lucide-react';

export default function StatCard({ type, amount, label }) {
  const isAvailable = type === 'available';
  const Icon = isAvailable ? CreditCard : Clock;
  
  const gradientClass = isAvailable 
    ? 'from-brand-500/20 to-brand-600/5 border-brand-500/20 group-hover:border-brand-500/40' 
    : 'from-orange-500/20 to-orange-600/5 border-orange-500/20 group-hover:border-orange-500/40';
    
  const iconColorClass = isAvailable ? 'text-brand-400' : 'text-orange-400';
  const labelColorClass = isAvailable ? 'text-brand-400' : 'text-orange-400';

  const formatCurrency = (paise) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format((paise || 0) / 100);
  };

  return (
    <div className={`glass-panel p-6 rounded-2xl flex flex-col justify-center relative overflow-hidden group transition-all duration-300 hover:shadow-2xl hover:shadow-${isAvailable ? 'brand' : 'orange'}-500/10 hover:-translate-y-1`}>
      {/* Background Gradient & Icon */}
      <div className={`absolute inset-0 bg-gradient-to-br ${gradientClass} opacity-50 transition-opacity group-hover:opacity-100`}></div>
      <div className="absolute -top-4 -right-4 p-4 opacity-5 group-hover:opacity-10 transition-opacity transform group-hover:scale-110 duration-500">
        <Icon className={`w-32 h-32 ${iconColorClass}`} />
      </div>
      
      {/* Content */}
      <div className="relative z-10">
        <div className="flex items-center space-x-2 mb-2">
          <Icon className={`w-5 h-5 ${iconColorClass} drop-shadow-[0_0_8px_currentColor]`} />
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-widest">{type} Balance</h2>
        </div>
        <div className="text-4xl lg:text-5xl font-extrabold text-white mb-2 tracking-tight">
          {formatCurrency(amount)}
        </div>
        <p className={`text-sm font-medium ${labelColorClass}`}>{label}</p>
      </div>
    </div>
  );
}
