import { Link, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useSession } from '../contexts/SessionContext';
import { Button } from './ui/button';
import { Badge } from './ui/badge';

export default function DoctorLayout() {
  const { user, logout } = useAuth();
  const { activeSession } = useSession();

  return (
    <div className="flex flex-col min-h-screen">
      {/* Header */}
      <header className="h-14 bg-slate-900 text-slate-100 flex items-center px-6 gap-4 shadow-md flex-shrink-0">
        <Link to="/patients" className="text-white font-bold text-lg hover:text-slate-200 transition-colors">
          Dental DICOM Portal
        </Link>

        <div className="flex-1" />

        {activeSession && (
          <Link to={`/session/${activeSession.id}`}>
            <Badge variant="success" className="gap-2 px-3 py-1.5 hover:bg-green-200 transition-colors cursor-pointer">
              <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              Active Session
            </Badge>
          </Link>
        )}

        <span className="text-sm text-slate-300">{user?.name}</span>

        <Button onClick={logout} variant="ghost" size="sm" className="text-slate-300 hover:text-white hover:bg-slate-800">
          Logout
        </Button>
      </header>

      {/* Page content */}
      <main className="flex-1 overflow-auto bg-slate-50">
        <Outlet />
      </main>
    </div>
  );
}
