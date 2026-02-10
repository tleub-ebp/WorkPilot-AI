import React, { useState } from 'react';
import { BaseEdge, EdgeLabelRenderer, getBezierPath, EdgeProps } from 'reactflow';

export const DefaultEdge: React.FC<EdgeProps> = (props) => {
  const { id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style, markerEnd, data, selected } = props;
  const [editing, setEditing] = useState(false);
  const [label, setLabel] = useState(data?.label || '');

  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });

  const handleDoubleClick = () => setEditing(true);
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => setLabel(e.target.value);
  const handleBlur = () => {
    setEditing(false);
    if (props.onEdgeLabelChange) props.onEdgeLabelChange(id, label);
  };
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      setEditing(false);
      if (props.onEdgeLabelChange) props.onEdgeLabelChange(id, label);
    }
  };

  return (
    <>
      <BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
      <EdgeLabelRenderer>
        <foreignObject
          width={120}
          height={40}
          x={labelX - 60}
          y={labelY - 20}
          style={{ overflow: 'visible' }}
        >
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 40 }}>
            <div onDoubleClick={handleDoubleClick} style={{ background: selected ? '#e0e7ff' : '#fff', borderRadius: 4, border: '1px solid #a5b4fc', padding: '2px 6px', minWidth: 40, minHeight: 20, fontSize: 13, cursor: 'pointer' }}>
              {editing ? (
                <input
                  autoFocus
                  value={label}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  onKeyDown={handleKeyDown}
                  style={{ width: 80, fontSize: 13, border: '1px solid #a5b4fc', borderRadius: 4, padding: 2 }}
                />
              ) : (
                <span>{label || '→'}</span>
              )}
            </div>
          </div>
        </foreignObject>
      </EdgeLabelRenderer>
    </>
  );
};
