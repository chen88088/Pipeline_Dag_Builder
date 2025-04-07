import { useCallback, useEffect, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  addEdge,
  useReactFlow,
} from 'reactflow';
import 'reactflow/dist/style.css';

const initialNodes = [];
const initialEdges = [];

const nodeTypesList = [
  { type: 'dag_id', label: 'Set Dag Name' },
  { type: 'generate_id', label: 'Generate Execution ID' },
  { type: 'create_env', label: 'Create Runtime Env' },
  { type: 'run_script', label: 'Run Script' },
  { type: 'upload_mlflow', label: 'Upload to MLflow' },
];

const componentParams = {
  dag_id: [{ key: 'dagName', label: 'DAG 名稱' }],
  generate_id: [{ key: 'prefix', label: 'ID 前綴' }],
};

export default function DagEditor() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [idCounter, setIdCounter] = useState(1);
  const [selectedNodes, setSelectedNodes] = useState([]);
  const [selectedEdges, setSelectedEdges] = useState([]);
  const [editingNode, setEditingNode] = useState(null);
  const [formState, setFormState] = useState({});
  const [dagJson, setDagJson] = useState(null);
  const { screenToFlowPosition } = useReactFlow();
  const reactFlowWrapper = useRef(null);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const nodeType = event.dataTransfer.getData('application/reactflow');

      if (!reactFlowWrapper.current) return;
      const bounds = reactFlowWrapper.current.getBoundingClientRect();

      const position = screenToFlowPosition({
        x: event.clientX - bounds.left,
        y: event.clientY - bounds.top,
      });

      const newNode = {
        id: `node-${idCounter}`,
        type: 'default',
        position,
        data: {
          type: nodeType,
          label: nodeTypesList.find((n) => n.type === nodeType)?.label || 'Unknown',
          config: {},
        },
        style: {
          padding: 10,
          border: '1px solid #888',
          borderRadius: 6,
          background: '#fff',
          width: 180,
        },
      };

      setNodes((nds) => nds.concat(newNode));
      setIdCounter((id) => id + 1);
    },
    [idCounter, screenToFlowPosition]
  );

  const onDragOver = (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  };

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Delete' || event.key === 'Backspace') {
        setNodes((nds) => nds.filter((n) => !selectedNodes.some((sn) => sn.id === n.id)));
        setEdges((eds) => eds.filter((e) => !selectedEdges.some((se) => se.id === e.id)));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedNodes, selectedEdges]);

  const handleNodeDoubleClick = (event, node) => {
    setEditingNode(node);
    setFormState(node.data.config || {});
  };

  const handleParamChange = (key, value) => {
    setFormState((prev) => ({ ...prev, [key]: value }));
  };

  const handleSaveConfig = () => {
    if (!editingNode) return;
    const newLabel = editingNode.data.type === 'dag_id'
      ? `${editingNode.data.label.split(':')[0]}: ${formState.dagName || ''}`
      : editingNode.data.label.split(':')[0];

    setNodes((nds) =>
      nds.map((n) =>
        n.id === editingNode.id
          ? {
              ...n,
              data: {
                ...n.data,
                config: { ...formState },
                label: newLabel,
              },
            }
          : n
      )
    );
    setEditingNode(null);
    setFormState({});
  };

  const generateDag = async () => {
    const dagName = nodes.find((n) => n.data.type === 'dag_id')?.data.config?.dagName || 'untitled_dag';
    const tasks = nodes
      .filter((n) => n.data.type !== 'dag_id')
      .map((node) => {
        const upstream = edges
          .filter((e) => e.target === node.id)
          .map((e) => e.source);

        return {
          id: node.id,
          type: node.data.type,
          config: node.data.config,
          upstream,
        };
      });

    const payload = {
      dag_name: dagName,
      tasks,
    };

    try {
      const res = await fetch('http://localhost:8000/deploy-dag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      alert('✅ DAG 已部署: ' + data.file);
    } catch (err) {
      alert('❌ 發送失敗：' + err.message);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
      <div style={{ width: 200, padding: 10, background: '#f0f0f0', borderRight: '1px solid #ccc' }}>
        <h4>元件清單</h4>
        {nodeTypesList.map((node) => (
          <div
            key={node.type}
            draggable
            onDragStart={(e) => e.dataTransfer.setData('application/reactflow', node.type)}
            style={{
              border: '1px solid #888',
              borderRadius: 6,
              padding: 10,
              marginBottom: 10,
              background: '#fff',
              cursor: 'grab',
              textAlign: 'center',
            }}
          >
            {node.label}
          </div>
        ))}
        <button onClick={generateDag} style={{ marginTop: 20 }}>🚀 產生並部署 DAG</button>
      </div>

      <div style={{ flexGrow: 1, height: '100%', position: 'relative' }} ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeDoubleClick={handleNodeDoubleClick}
          onSelectionChange={({ nodes, edges }) => {
            setSelectedNodes(nodes);
            setSelectedEdges(edges);
          }}
          fitView
        >
          <Background />
          <Controls />
        </ReactFlow>

        {editingNode && (
          <div
            style={{
              position: 'absolute',
              top: 10,
              left: 220,
              background: '#fff',
              padding: 10,
              border: '1px solid #aaa',
              borderRadius: 6,
              boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
              zIndex: 10,
              minWidth: 200,
            }}
          >
            <h4 style={{ margin: '0 0 8px 0' }}>{editingNode.data.label.split(':')[0]} 設定</h4>
            {componentParams[editingNode.data.type]?.map((param) => (
              <div key={param.key} style={{ marginBottom: 6 }}>
                <label>{param.label}</label>
                <input
                  type="text"
                  value={formState[param.key] || ''}
                  onChange={(e) => handleParamChange(param.key, e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>
            ))}
            <button onClick={handleSaveConfig} style={{ marginTop: 6 }}>儲存</button>
          </div>
        )}
      </div>
    </div>
  );
}
