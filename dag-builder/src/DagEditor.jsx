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
import NodeConfigModal from './NodeConfigModal';

const initialNodes = [];
const initialEdges = [];

const nodeTypesList = [
  { type: 'dag_id', label: 'Set Dag Name' },
  { type: 'generate_id', label: 'Generate Execution ID' },
  { type: 'create_env', label: 'Create Runtime Environment' },
  { type: 'register_dag', label: 'Register Workflow' },
  { type: 'download_dataset', label: 'Download Dataset' },
  { type: 'download_code', label: 'Download Code Repository' },
  { type: 'add_config', label: 'Inject Config' },
  { type: 'run_script', label: 'Execute Training Script' },
  { type: 'upload_mlflow', label: 'Upload Experiment' },
  { type: 'upload_log', label: 'Upload Log' },
  { type: 'release_env', label: 'Release Runtime Environment' },
];

const componentParams = {
  dag_id: [{ key: 'dagName', label: 'DAG 名稱' }],
  generate_id: [{ key: 'prefix', label: 'ID 前綴' }],
};

const paramSchemas = {
  download_dataset: [
    { key: 'dataset_name', label: 'Dataset Name', type: 'text' },
    { key: 'dataset_version', label: 'Dataset Version', type: 'text' },
    { key: 'dvc_repo', label: 'DVC Repo URL', type: 'text' },
  ],
  create_env: [
    { key: 'image_name', label: 'Image Name', type: 'text' },
    { key: 'image_tag', label: 'Image Tag', type: 'text' },
    { key: 'export_port', label: 'Export Port', type: 'number' },
  ],
  run_script: [
    { key: 'script_list', label: 'Script(s)', type: 'textlist' },
    { key: 'image_name', label: 'Image Name', type: 'text' },
  ],
  upload_mlflow: [
    { key: 'script_name', label: 'MLflow Script Name', type: 'text' },
  ],
  
  upload_log: [
    { key: 'log_path', label: 'Log File Path', type: 'text' },
  ],
  
  release_env: [
    { key: 'target_service', label: 'Service Name to Release', type: 'text' },
  ],
  // 可擴充其他元件
}

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

  const getDefaultLabel = (type, config = {}) => {
    const baseLabel = nodeTypesList.find((n) => n.type === type)?.label || 'Unknown';
  
    // 只有 dag_id 類型要加上名稱
    if (type === 'dag_id' && config.dagName) {
      return `${baseLabel}: ${config.dagName}`;
    }
  
    return baseLabel;
  };

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
  
      const config = {};  // 預設空 config
      const label = getDefaultLabel(nodeType, config);
  
      const newNode = {
        id: `node-${idCounter}`,
        type: 'default',
        position,
        data: {
          type: nodeType,
          config,
          label, // ✅ 初始即有 label
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
      const activeTag = document.activeElement?.tagName;
      const isTyping = activeTag === 'INPUT' || activeTag === 'TEXTAREA';
  
      if (isTyping) return; // 💡 正在輸入中，不處理刪除
  
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
  
    const type = editingNode.data.type;
    const baseLabel = nodeTypesList.find((n) => n.type === type)?.label || type;
    const config = { ...formState };
  
    const newLabel =
      type === 'dag_id' && config.dagName
        ? `${baseLabel}: ${config.dagName}`
        : baseLabel;
  
    setNodes((nds) =>
      nds.map((n) =>
        n.id === editingNode.id
          ? {
              ...n,
              data: {
                ...n.data,
                config,
                label: newLabel || baseLabel, // fallback for first render
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
    // 這行會把 JSON 印出來
    console.log("產出 JSON:", payload);
    setDagJson(payload); // 💡 顯示 JSON 結構

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

        {dagJson && (
          <div style={{ position: 'absolute', bottom: 0, right: 0, width: '40%', maxHeight: '40%', overflowY: 'auto', background: '#f9f9f9', border: '1px solid #ccc', padding: 10, fontSize: 12 }}>
            <strong>產出 JSON 預覽</strong>
            <pre>{JSON.stringify(dagJson, null, 2)}</pre>
          </div>
        )}

        {editingNode && (
          <NodeConfigModal
            node={editingNode}
            formState={formState}
            onChange={handleParamChange}
            onSave={handleSaveConfig}
            onClose={() => setEditingNode(null)}
            paramSchemas={paramSchemas}
            componentParams={componentParams}
          />
        )}       

        
      </div>
    </div>
  );
}
