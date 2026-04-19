import { Navigate, Route, Routes } from 'react-router-dom';
import { Shell } from './layout/Shell';
import { Overview } from './pages/Overview';
import { RunsList } from './pages/RunsList';
import { RunDetail } from './pages/RunDetail';
import { ChangesList, ChangeDetail } from './pages/ChangesReview';
import { Health } from './pages/Health';
import { Memory } from './pages/Memory';
import { Lookup } from './pages/Lookup';
import { Settings } from './pages/Settings';
import { NewRun } from './pages/NewRun';
import { ProjectView, WorkUnitView } from './pages/ProjectView';

export default function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<Overview />} />
        <Route path="/runs" element={<RunsList />} />
        <Route path="/changes" element={<ChangesList />} />
        <Route path="/changes/:changeId" element={<ChangeDetail />} />
        <Route path="/memory" element={<Memory />} />
        <Route path="/health" element={<Health />} />
        <Route path="/lookup" element={<Lookup />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/p/:projectId" element={<ProjectView />} />
        <Route path="/p/:projectId/new" element={<NewRun />} />
        <Route path="/p/:projectId/wu/:workUnitId" element={<WorkUnitView />} />
        <Route path="/p/:projectId/wu/:workUnitId/new" element={<NewRun />} />
        <Route path="/p/:projectId/wu/:workUnitId/r/:runId" element={<RunDetail />} />
        <Route path="*" element={<div className="p-8 text-muted">Not found.</div>} />
      </Route>
    </Routes>
  );
}
