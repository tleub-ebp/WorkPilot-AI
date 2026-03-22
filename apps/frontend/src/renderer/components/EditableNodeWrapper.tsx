import React, { useState, useEffect } from 'react';
import { EditableNode } from './EditableNode';
import { NodeProps } from 'reactflow';

export const EditableNodeWrapper: React.FC<NodeProps> = (props) => {
  const { data } = props;
  const [label, setLabel] = useState(data.label || '');

  useEffect(() => {
    setLabel(data.label || '');
  }, [data.label]);

  // onRename callback pour ReactFlow
  const handleRename = (nodeId: string, newLabel: string) => {
    if (data.onRename) data.onRename(nodeId, newLabel);
    setLabel(newLabel);
  };

  return (
    <EditableNode {...props} data={{ ...data, label, onRename: handleRename }} />
  );
};
