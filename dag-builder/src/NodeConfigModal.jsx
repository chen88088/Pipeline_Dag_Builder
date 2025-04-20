import React from 'react';

export default function NodeConfigModal({
  node,
  formState,
  onChange,
  onSave,
  onClose,
  paramSchemas,
  componentParams
}) {
  if (!node) return null;

  const fields = componentParams[node.data.type] || paramSchemas[node.data.type] || [];

  return (
    <div
      style={{
        position: 'absolute',
        top: 10,
        left: 220,
        background: '#fff',
        padding: 10,
        paddingBottom: 50,
        border: '1px solid #aaa',
        borderRadius: 6,
        boxShadow: '0 2px 6px rgba(0,0,0,0.1)',
        zIndex: 10,
        minWidth: 250,
        minHeight: 180,
      }}
    >
      <h4 style={{ margin: '0 0 8px 0' }}>
        {node.data.label.split(':')[0]} 設定
      </h4>

      {fields.map((param) => (
        <div key={param.key} style={{ marginBottom: 6 }}>
          <label>{param.label}</label>
            {param.type === 'textlist' ? (
                <textarea
                    rows={3}
                    value={(formState[param.key] || []).join('\n')}
                    onChange={(e) =>
                    onChange(param.key, e.target.value.split('\n').filter((line) => line.trim() !== ''))
                    }
                    style={{ width: '100%' }}
                    placeholder="每行一個腳本名稱"
                />
                ) : (
                <input
                    type={param.type === 'number' ? 'number' : 'text'}
                    value={formState[param.key] || ''}
                    onChange={(e) => onChange(param.key, e.target.value)}
                    style={{ width: '100%' }}
                />
            )}
        </div>
      ))}

      {/* 儲存按鈕 */}
      <button
        onClick={onSave}
        style={{
          position: 'absolute',
          left: 10,
          bottom: 10,
          background: '#e6f4ea',
          border: '1px solid #ccc',
          padding: '4px 10px',
          borderRadius: 4,
          color: '#333',
          cursor: 'pointer',
          fontSize: 14,
        }}
      >
        💾 儲存
      </button>

      {/* 關閉按鈕 */}
      <button
        onClick={onClose}
        style={{
          position: 'absolute',
          right: 10,
          bottom: 10,
          background: '#f8f8f8',
          border: '1px solid #ccc',
          padding: '4px 10px',
          borderRadius: 4,
          color: '#333',
          cursor: 'pointer',
          fontSize: 14,
        }}
      >
        ❌ 關閉
      </button>
    </div>
  );
}
