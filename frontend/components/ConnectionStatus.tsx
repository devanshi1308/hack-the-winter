import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api';

export default function ConnectionStatus() {
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    checkBackend();
    const interval = setInterval(checkBackend, 15000); // Check every 15 seconds
    return () => clearInterval(interval);
  }, []);

  const checkBackend = async () => {
    try {
      const health = await apiClient.health();
      setBackendStatus(health.status === 'offline' ? 'offline' : 'online');
    } catch {
      setBackendStatus('offline');
    }
  };

  if (backendStatus === 'online') return null; // Only show when there's an issue

  return (
    <div className="fixed top-4 right-4 z-50 bg-yellow-100 dark:bg-yellow-900 border border-yellow-400 text-yellow-700 dark:text-yellow-300 px-3 py-2 rounded-lg text-sm">
      {backendStatus === 'checking' ? (
        '🔄 Checking connection...'
      ) : (
        '⚠️ Offline mode - data saved locally'
      )}
    </div>
  );
}
