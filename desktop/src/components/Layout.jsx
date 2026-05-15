import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import StatusBar from './StatusBar'

export default function Layout() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-end px-6 py-3 border-b border-slate-800 bg-slate-950 shrink-0">
          <StatusBar />
        </header>
        {/* Page content */}
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
