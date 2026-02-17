import { Link, NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/button';
import { Separator } from './ui/separator';

export default function AdminLayout() {
  const { user, logout } = useAuth();

  const navLinks = [
    { to: '/admin/sessions', label: 'Sessions' },
    { to: '/admin/assignments', label: 'Assignments' },
    { to: '/admin/audit-logs', label: 'Audit Logs' },
    { to: '/admin/health', label: 'System Health' },
  ];

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-56 bg-slate-900 text-slate-100 flex flex-col flex-shrink-0">
        <div className="px-5 py-4 border-b border-slate-700">
          <h1 className="text-white font-bold text-lg">Admin Dashboard</h1>
          <p className="text-slate-400 text-sm mt-1">{user?.name}</p>
        </div>

        <nav className="flex-1 py-4">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `block px-5 py-2.5 mx-2 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-slate-800 text-white border-l-2 border-blue-500 pl-[18px]'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <Separator className="bg-slate-700" />

        <div className="p-4 flex gap-2">
          <Button variant="ghost" size="sm" asChild className="flex-1 text-slate-300 hover:text-white hover:bg-slate-800">
            <Link to="/">Dashboard</Link>
          </Button>
          <Button onClick={logout} variant="ghost" size="sm" className="flex-1 text-slate-300 hover:text-white hover:bg-slate-800">
            Logout
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto bg-slate-50">
        <Outlet />
      </main>
    </div>
  );
}
