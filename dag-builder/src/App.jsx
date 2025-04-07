import { ReactFlowProvider } from 'reactflow';
import DagEditor from './DagEditor'; // 分離邏輯組件

export default function App() {
  return (
    <ReactFlowProvider>
      <DagEditor />
    </ReactFlowProvider>
  );
}