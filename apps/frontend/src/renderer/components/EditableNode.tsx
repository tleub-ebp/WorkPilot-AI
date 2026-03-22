import React, { useState } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';

// Utilise les couleurs du thème utilisateur via CSS vars (définies dans globals.css)
// Fallback sur des couleurs par défaut si non définies
const getUserNodeColors = () => ({
  nodeBg: 'var(--card, #f3f4f6)',
  nodeBorder: 'var(--primary, #a5b4fc)',
  nodeText: 'var(--foreground, #1e293b)',
  nodeSelected: 'var(--primary, #e0e7ff)',
});

export const EditableNode: React.FC<NodeProps> = ({ id, data, selected, xPos, yPos, dragging, ...rest }) => {
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(data.label || '');
  // Prend les couleurs du thème utilisateur
  const theme = getUserNodeColors();

  const handleDoubleClick = () => setEditing(true);
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => setLabel(e.target.value);
  const handleBlur = () => {
    setEditing(false);
    if (data.onRename) data.onRename(id, label);
  };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      setEditing(false);
      if (data.onRename) data.onRename(id, label);
    }
  };

  return (
    <div
      onDoubleClick={handleDoubleClick}
      style={{
        padding: 8,
        minWidth: 80,
        background: selected ? theme.nodeSelected : theme.nodeBg,
        borderRadius: 6,
        border: `1.5px solid ${theme.nodeBorder}`,
        color: theme.nodeText,
        boxShadow: dragging ? '0 2px 8px rgba(0,0,0,0.08)' : undefined,
        transition: 'background 0.2s, border 0.2s',
      }}
    >
      {editing ? (
        <input
          autoFocus
          value={label}
          onChange={handleChange}
          onBlur={handleBlur}
          onKeyDown={handleKeyDown}
          style={{ width: '100%', fontWeight: 600, fontSize: 14, border: `1px solid ${theme.nodeBorder}`, borderRadius: 4, padding: 2, color: theme.nodeText, background: theme.nodeBg }}
        />
      ) : (
        <span style={{ fontWeight: 600, fontSize: 14 }}>{label}</span>
      )}
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};