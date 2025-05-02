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
};

const paramSchemas = {
  // create_env: [
  //   { key: 'image_name', label: 'Image Name', type: 'text' },
  //   { key: 'image_tag', label: 'Image Tag', type: 'text' },
  //   { key: 'export_port', label: 'Export Port', type: 'number' },
  // ],
  download_dataset: [
    { key: 'dataset_name', label: 'Dataset Name', type: 'text' },
    { key: 'dataset_version', label: 'Dataset Version', type: 'text' },
    { key: 'dvc_repo', label: 'DVC Repo URL', type: 'text' },
  ],
  download_code: [
    { key: 'code_repo_url', label: 'Code Repo URL', type: 'text' },
  ],
  add_config: [
    { key: 'config_params', label: 'Custom Params', type: 'kvlist' },
  ],
  run_script: [
    { key: 'script_list', label: 'Script(s)', type: 'textlist' },
    { key: 'image_name', label: 'Image Name', type: 'text' },
  ],
  upload_mlflow: [
    { key: 'script_name', label: 'MLflow Script Name', type: 'text' },
  ],
  
  // upload_log: [
  //   { key: 'log_path', label: 'Log File Path', type: 'text' },
  // ],
  
  // release_env: [
  //   { key: 'target_service', label: 'Service Name to Release', type: 'text' },
  // ],
  // 可擴充其他元件
}

export default function DagEditor() {
  const [dagId, setDagId] = useState(null); // ⬅️ 加這一行
  const [executionId, setExecutionId] = useState(null); // ⬅️ 加這一行
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
  const [triggerUrl, setTriggerUrl] = useState(null);
  const [startPolling, setStartPolling] = useState(false);
  const [dagRunId, setDagRunId] = useState(null);
  const [bodyConfig, setBodyConfig] = useState(null);
  const [reservedExpRunId, setReservedExpRunId] = useState()
  

  const [mlflowUrl, setMlflowUrl] = useState(null);
  const [kibanaUrl, setKibanaUrl] = useState(null);
  const [minioUrl, setMinioUrl] = useState(null);

  // useEffect(() => {
  //   if (dagId && dagRunId) {
  //     const interval = setInterval(async () => {
  //       const response = await fetch(`http://localhost:8000/dag-status?dag_id=${dagId}&dag_run_id=${dagRunId}`);
  //       const data = await response.json();

  //       if (data.state === "success") {
  //         clearInterval(interval);
  //         alert("✅ DAG 執行完成！");

  //         setMlflowUrl(data.mlflow_url);
  //         setKibanaUrl(data.kibana_url);
  //         setMinioUrl(data.minio_url);
  //       }
  //     }, 5000);

  //     return () => clearInterval(interval);
  //   }
  // }, [dagId, dagRunId]);

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
    if (dagId && dagRunId && startPolling) {
      const interval = setInterval(async () => {
        try {
          const response = await fetch(`http://localhost:8000/dag-status?dag_id=${dagId}&execution_id=${executionId}&dag_run_id=${dagRunId}&reserved_exp_run_id=${reservedExpRunId}`);
          if (response.status === 404) {
            console.log("DAG Run 還沒註冊完成，稍後再試");
            return; // 這次跳過
          }
  
          const data = await response.json();
  
          if (data.state === "success") {
            clearInterval(interval);
            alert("✅ DAG 執行完成！");
            setMlflowUrl(data.mlflow_url);
            setKibanaUrl(data.kibana_url);
            setMinioUrl(data.minio_url);
          }
          else if (data.state === "failed") {
            clearInterval(interval);
            alert("❌ DAG 執行失敗，請檢查 Airflow Log！");
          }
            // 如果是 running, queued, 等狀態就繼續輪詢
          else if (response.status === 404) {
            console.log("⏳ DAG Run 還沒註冊，稍後再試...");
          }
          // pollingAttempts += 1;
          // if (pollingAttempts > 12) {  // 12次 = 約1分鐘
          //  clearInterval(interval);
          //  alert("⚠️ DAG 超過1分鐘未完成，請手動確認 Airflow！");
          //}
        } catch (err) {
          console.error("查詢 DAG Run 狀態失敗", err);
        }
      }, 5000);
  
      return () => clearInterval(interval);
    }
  }, [dagId, dagRunId, startPolling]);

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
    console.log("點到的節點類型：", node.data.type);
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
      if (res.ok) {
        alert("✅ DAG 已部署成功: " + data.dag_id);
        setTriggerUrl(data.airflow_url);  // optional: 這是原本開 UI 用的
        setDagId(data.dag_id);            // 實際用來觸發 API
        setBodyConfig(data.body_config);   // 加這行！把 body_config存起來
        setExecutionId(data.execution_id);   // 加這行！把 execution_id存起來
      } else {
        alert("❌ DAG 部署失敗: " + data.detail);
      }
    } catch (err) {
      alert("❌ 伺服器錯誤: " + err.message);
    }
  };

  const triggerDAG = async () => {
    if (!dagId) {
      alert("❌ 無法觸發，DAG ID 未設定");
      return;
    }
    if (!bodyConfig) {
      alert("❌ 無法觸發，body_config 未設定");
      return;
    }
  
    const experimentName = bodyConfig.DAG_ID;  // 用 DAG_ID 當 experiment_name
    const executionId = bodyConfig.EXECUTION_ID;  // 本次 execution_id
    const experimentRunName = `${experimentName}_${executionId}`;  // ✅ 正確格式，dag_id + execution_id
  
    const response = await fetch("http://localhost:8000/trigger-dag", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ 
        dag_id: dagId,
        conf: {
          experiment_name: experimentName,
          experiment_run_name: experimentRunName,
          body_config: bodyConfig
        }
       }),
    });
  
    const data = await response.json();
  
    if (response.ok) {
      alert("✅ 成功觸發 DAG: " + data.dag_run_id);
      const encodedRunId = encodeURIComponent(data.dag_run_id);  // 必須這一行！！encode成安全格式
      setDagRunId(encodedRunId);  // 這樣才存的是正確的 run_id！
      setReservedExpRunId(data.reserved_exp_run_id); // 用來之後按按鈕跳MLflow！

      // 💡 加這個：
      setTimeout(() => {
        setStartPolling(true);  // 可以控制開始輪詢
      }, 5000);  // 5秒後再啟動輪詢
    } else {
      alert("❌ 觸發失敗: " + data.detail);
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
        <button 
          onClick={generateDag} 
          // style={{ marginTop: 20 }}
          style={{
            background: '#28a745',
            color: '#fff',
            padding: '10px 16px',
            borderRadius: 6,
            border: 'none',
            cursor: 'pointer',
          }}
        >
            
            產生並部署 DAG

        </button>
        {dagId && (
          <div style={{ marginTop: 10 }}>
            <button
              onClick={triggerDAG}
              style={{
                background: '#007bff',
                color: '#fff',
                padding: '10px 16px',
                borderRadius: 6,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Trigger DAG
            </button>
          </div>
        )}
      </div>

      {mlflowUrl && kibanaUrl && minioUrl && (
        <div
          style={{
            marginTop: 10,
            display: 'flex',
            flexDirection: 'column', // 🔥 這一行讓按鈕直排
            gap: '8px'               // ✅ 每個按鈕之間有間距
          }}
        >
          <a href={mlflowUrl} target="_blank" rel="noopener noreferrer">
            <button
              style={{
                background: '#6f42c1',
                color: '#fff',
                padding: '8px 12px',
                borderRadius: 6,
                border: 'none',
                cursor: 'pointer',
                width: '100%',
              }}
            >
              查看 MLflow 實驗
            </button>
          </a>
          <a href={kibanaUrl} target="_blank" rel="noopener noreferrer">
            <button
              style={{
                background: '#1abc9c',
                color: '#fff',
                padding: '8px 12px',
                borderRadius: 6,
                border: 'none',
                cursor: 'pointer',
                width: '100%',
              }}
            >
              查看 Kibana 日誌
            </button>
          </a>
          <a href={minioUrl} target="_blank" rel="noopener noreferrer">
            <button
              style={{
                background: '#007bff',
                color: '#fff',
                padding: '8px 12px',
                borderRadius: 6,
                border: 'none',
                cursor: 'pointer',
                width: '100%',
              }}
            >
              查看 MinIO 輸出
            </button>
          </a>
        </div>
      )}

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
