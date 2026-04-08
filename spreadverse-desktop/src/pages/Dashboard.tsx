import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const handleLogout = () => {
    apiClient.clearTokens();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Sidebar - Glassmorphism Style */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-20'
        } bg-white/5 backdrop-blur-xl border-r border-white/10 text-white transition-all duration-300 flex flex-col shadow-2xl`}
        style={{
          boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        }}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-white/10 bg-gradient-to-r from-white/5 to-transparent">
          <div className="flex items-center justify-between">
            {sidebarOpen && (
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-gradient-to-br from-cyan-500 to-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-cyan-500/50">
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                  </svg>
                </div>
                <span className="font-bold text-lg bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent">SpreadVerse</span>
              </div>
            )}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-white/10 rounded-lg transition-all duration-200 hover:scale-110"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={sidebarOpen ? 'M11 19l-7-7 7-7m8 14l-7-7 7-7' : 'M13 5l7 7-7 7M5 5l7 7-7 7'}
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="flex-1 p-4 space-y-2">
          <NavItem
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
              />
            }
            label="Dashboard"
            active={true}
            collapsed={!sidebarOpen}
          />
          <NavItem
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
              />
            }
            label="Customers"
            active={false}
            collapsed={!sidebarOpen}
          />
          <NavItem
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            }
            label="Analytics"
            active={false}
            collapsed={!sidebarOpen}
          />
          <NavItem
            icon={
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
            }
            label="Settings"
            active={false}
            collapsed={!sidebarOpen}
          />
        </nav>

        {/* Logout Button */}
        <div className="p-4 border-t border-white/10 bg-gradient-to-r from-white/5 to-transparent">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-gradient-to-r from-red-500/20 to-red-600/20 hover:from-red-500/30 hover:to-red-600/30 backdrop-blur-sm border border-red-500/30 rounded-lg transition-all duration-200 hover:scale-105 hover:shadow-lg hover:shadow-red-500/20"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
            {sidebarOpen && <span>Logout</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {/* Top Bar - Glassmorphism */}
        <header className="bg-white/5 backdrop-blur-md border-b border-white/10 shadow-xl">
          <div className="px-8 py-4">
            <h1 className="text-2xl font-bold text-white">
              Welcome to SpreadVerse Super Admin
            </h1>
            <p className="text-cyan-300/80 mt-1">
              Multi-tenant Enterprise CRM Dashboard
            </p>
          </div>
        </header>

        {/* Dashboard Content */}
        <div className="p-8">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatsCard
              title="Total Customers"
              value="1,234"
              change="+12.5%"
              positive={true}
            />
            <StatsCard
              title="Active Leads"
              value="456"
              change="+8.2%"
              positive={true}
            />
            <StatsCard
              title="Revenue"
              value="$89.2K"
              change="+15.3%"
              positive={true}
            />
            <StatsCard
              title="Conversion Rate"
              value="24.8%"
              change="-2.1%"
              positive={false}
            />
          </div>

          {/* Placeholder Content - Glassmorphism Card */}
          <div className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-xl shadow-2xl p-8 hover:bg-white/10 transition-all duration-300">
            <h2 className="text-xl font-semibold text-white mb-4">
              Recent Activity
            </h2>
            <div className="text-center py-12 text-cyan-300/60">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-cyan-400/50"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
              <p>Dashboard features coming soon...</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

// Navigation Item Component
interface NavItemProps {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  collapsed: boolean;
}

const NavItem: React.FC<NavItemProps> = ({ icon, label, active, collapsed }) => (
  <button
    className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition-all duration-200 transform ${
      active
        ? 'bg-gradient-to-r from-cyan-500/20 to-blue-500/20 text-white border border-cyan-500/30 shadow-lg shadow-cyan-500/20 scale-105'
        : 'text-slate-300 hover:bg-white/10 hover:text-white hover:scale-105 hover:shadow-lg'
    }`}
  >
    <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      {icon}
    </svg>
    {!collapsed && <span className="font-medium">{label}</span>}
  </button>
);

// Stats Card Component
interface StatsCardProps {
  title: string;
  value: string;
  change: string;
  positive: boolean;
}

const StatsCard: React.FC<StatsCardProps> = ({ title, value, change, positive }) => (
  <div
    className="bg-white/5 backdrop-blur-lg border border-white/10 rounded-xl shadow-2xl p-6 hover:bg-white/10 transition-all duration-300 transform hover:scale-105 hover:-translate-y-1 hover:shadow-cyan-500/20 cursor-pointer group"
    style={{
      boxShadow: '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
    }}
  >
    <p className="text-sm text-cyan-300/70 mb-2 group-hover:text-cyan-300 transition-colors">{title}</p>
    <p className="text-3xl font-bold text-white mb-2 bg-gradient-to-r from-white to-cyan-200 bg-clip-text text-transparent">{value}</p>
    <p className={`text-sm font-medium ${positive ? 'text-green-400' : 'text-red-400'}`}>
      {change} from last month
    </p>
  </div>
);

export default Dashboard;
