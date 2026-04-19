import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function Shell() {
  return (
    <div className="flex h-screen w-screen bg-bg text-text">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar />
        <main className="flex-1 overflow-hidden min-h-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
