import { useEffect, useState } from 'react';
import axios from 'axios';
import { Activity, CheckCircle, XCircle } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

function App() {
  const [merchant, setMerchant] = useState(() => {
    try {
      const stored = localStorage.getItem('merchant');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [balance, setBalance] = useState({ available: 0, held: 0 });
  const [payouts, setPayouts] = useState([]);
  const [recentCredits, setRecentCredits] = useState([]);
  const [recentDebits, setRecentDebits] = useState([]);
  const [amount, setAmount] = useState('');
  const [bankAccount, setBankAccount] = useState('');
  const [name, setName] = useState('');
  const [initialCreditInr, setInitialCreditInr] = useState('1000');
  const [loading, setLoading] = useState(false);
  const [merchantLoading, setMerchantLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const persistMerchant = (merchantData) => {
    localStorage.setItem('merchant', JSON.stringify(merchantData));
    setMerchant(merchantData);
  };

  const handleClearMerchant = () => {
    localStorage.removeItem('merchant');
    setMerchant(null);
    setBalance({ available: 0, held: 0 });
    setPayouts([]);
    setRecentCredits([]);
    setRecentDebits([]);
    setError('');
    setSuccess('');
  };

  const fetchDashboardData = async () => {
    if (!merchant?.id) {
      return;
    }

    try {
      const response = await axios.get(`${API_BASE}/merchants/${merchant.id}/dashboard`);
      const payload = response.data;
      setBalance({
        available: payload.merchant.available_balance,
        held: payload.merchant.held_balance,
      });
      setPayouts(payload.payouts || []);
      setRecentCredits(payload.recent_credits || []);
      setRecentDebits(payload.recent_debits || []);
    } catch (err) {
      if (err.response?.status === 404) {
        localStorage.removeItem('merchant');
        setMerchant(null);
        setError('Saved merchant was not found. Please create a merchant again.');
      }
      setBalance({ available: 0, held: 0 });
      setPayouts([]);
      setRecentCredits([]);
      setRecentDebits([]);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 3000);
    return () => clearInterval(interval);
  }, [merchant]);

  const handleMerchantCreate = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (!name.trim()) {
      setError('Merchant name is required.');
      return;
    }

    const creditValue = Number(initialCreditInr);
    if (Number.isNaN(creditValue) || creditValue < 0) {
      setError('Initial credit must be a valid non-negative number.');
      return;
    }

    setMerchantLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/merchants`, {
        name: name.trim(),
        initial_credit_paise: Math.round(creditValue * 100),
      });
      persistMerchant(response.data);
      setName('');
      setInitialCreditInr('1000');
      setSuccess('Merchant created successfully.');
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to create merchant.');
    } finally {
      setMerchantLoading(false);
    }
  };

  const handlePayoutSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    if (!merchant?.id) {
      setError('Please create or select a merchant first.');
      return;
    }

    if (!amount || Number(amount) <= 0) {
      setError('Please enter a valid amount.');
      return;
    }

    if (!bankAccount.trim()) {
      setError('Please enter a bank account ID.');
      return;
    }

    setLoading(true);
    try {
      await axios.post(
        `${API_BASE}/payouts`,
        {
          merchant_id: merchant.id,
          amount_paise: Math.round(Number(amount) * 100),
          bank_account_id: bankAccount.trim(),
        },
        { headers: { 'Idempotency-Key': uuidv4() } }
      );
      setAmount('');
      setBankAccount('');
      setSuccess('Payout requested successfully.');
      fetchDashboardData();
    } catch (err) {
      if (err.response?.status === 404) {
        localStorage.removeItem('merchant');
        setMerchant(null);
        setError('Merchant not found. Please create a merchant again.');
      } else {
        setError(err.response?.data?.error || err.message || 'Failed to process payout.');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (paise) =>
    new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
    }).format((paise || 0) / 100);

  const statusBadge = (payoutStatus) => {
    switch (payoutStatus) {
      case 'COMPLETED':
        return <span className="text-xs px-2 py-1 rounded bg-green-100 text-green-700">Completed</span>;
      case 'FAILED':
        return <span className="text-xs px-2 py-1 rounded bg-red-100 text-red-700">Failed</span>;
      case 'PROCESSING':
        return <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-700">Processing</span>;
      default:
        return <span className="text-xs px-2 py-1 rounded bg-yellow-100 text-yellow-700">Pending</span>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-cyan-700 shadow">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <div>
            <h1 className="text-white text-2xl font-bold">Playto Payout Engine</h1>
            <p className="text-cyan-100 text-sm mt-1 max-w-3xl">
              Build a service where merchants can see their balance, request payouts, and track payout status.
              The service must handle the concurrency, idempotency, and data integrity problems that real payment
              systems fail at.
            </p>
          </div>
          <span className="text-cyan-100 text-sm flex items-center gap-1">
            <Activity className="w-4 h-4" /> Live
          </span>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-4 md:p-8 space-y-8">
        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border p-5">
            <div className="flex justify-between items-center mb-3">
              <h2 className="font-semibold">Merchant Setup</h2>
              {merchant && (
                <button className="text-sm text-red-600" onClick={handleClearMerchant}>
                  Clear
                </button>
              )}
            </div>
            {merchant && (
              <div className="text-sm bg-slate-50 border rounded p-3 mb-4">
                <div className="font-medium">{merchant.name}</div>
                <div className="text-xs break-all">{merchant.id}</div>
              </div>
            )}
            <form onSubmit={handleMerchantCreate} className="space-y-3">
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Merchant name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Initial balance in INR"
                type="number"
                step="0.01"
                value={initialCreditInr}
                onChange={(e) => setInitialCreditInr(e.target.value)}
              />
              <button className="w-full bg-cyan-700 text-white py-2 rounded" disabled={merchantLoading}>
                {merchantLoading ? 'Creating...' : 'Create Merchant'}
              </button>
            </form>
          </div>

          <div className="bg-white rounded-xl border p-5 grid grid-cols-2 gap-4">
            <div className="bg-slate-50 rounded p-4">
              <div className="text-sm text-slate-500">Available</div>
              <div className="text-2xl font-bold">{formatCurrency(balance.available)}</div>
            </div>
            <div className="bg-slate-50 rounded p-4">
              <div className="text-sm text-slate-500">Held</div>
              <div className="text-2xl font-bold">{formatCurrency(balance.held)}</div>
            </div>
          </div>
        </section>

        {error && (
          <div className="p-3 rounded border border-red-200 bg-red-50 text-red-700 flex items-center gap-2">
            <XCircle className="w-4 h-4" /> {error}
          </div>
        )}
        {success && (
          <div className="p-3 rounded border border-green-200 bg-green-50 text-green-700 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" /> {success}
          </div>
        )}

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border p-5">
            <h3 className="font-semibold mb-3">Request Payout</h3>
            <form onSubmit={handlePayoutSubmit} className="space-y-3">
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Amount in INR"
                type="number"
                step="0.01"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="Bank account ID"
                value={bankAccount}
                onChange={(e) => setBankAccount(e.target.value)}
              />
              <button className="w-full bg-cyan-700 text-white py-2 rounded" disabled={loading}>
                {loading ? 'Submitting...' : 'Submit'}
              </button>
            </form>
          </div>

          <div className="bg-white rounded-xl border p-5 lg:col-span-2">
            <h3 className="font-semibold mb-3">Payout History</h3>
            <div className="overflow-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b">
                    <th className="py-2">Created</th>
                    <th className="py-2">Bank</th>
                    <th className="py-2">Amount</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {payouts.map((payout) => (
                    <tr key={payout.id} className="border-b">
                      <td className="py-2">{new Date(payout.created_at).toLocaleString()}</td>
                      <td className="py-2">{payout.bank_account_id}</td>
                      <td className="py-2 font-medium">{formatCurrency(payout.amount_paise)}</td>
                      <td className="py-2">{statusBadge(payout.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-xl border p-5">
            <h3 className="font-semibold mb-3">Recent Credits</h3>
            <ul className="space-y-2 text-sm">
              {recentCredits.map((entry) => (
                <li key={entry.id} className="flex justify-between border-b pb-2">
                  <span>{new Date(entry.created_at).toLocaleString()}</span>
                  <span className="font-medium text-green-700">+{formatCurrency(entry.amount_paise)}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="bg-white rounded-xl border p-5">
            <h3 className="font-semibold mb-3">Recent Debits</h3>
            <ul className="space-y-2 text-sm">
              {recentDebits.map((entry) => (
                <li key={entry.id} className="flex justify-between border-b pb-2">
                  <span>{new Date(entry.created_at).toLocaleString()}</span>
                  <span className="font-medium text-red-700">-{formatCurrency(entry.amount_paise)}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}

export default App;
