import { Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/MainLayout";
import TaskBoard from "./pages/TaskBoard";
import PipelineWorkbench from "./pages/PipelineWorkbench";
import SettingsPage from "./pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Navigate to="/tasks" replace />} />
        <Route path="tasks" element={<TaskBoard />} />
        <Route path="pipeline/:id" element={<PipelineWorkbench />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
