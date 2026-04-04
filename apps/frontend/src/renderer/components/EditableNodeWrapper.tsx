import type React from "react";
import { useEffect, useState } from "react";
import type { NodeProps } from "reactflow";
import { EditableNode } from "./EditableNode";

export const EditableNodeWrapper: React.FC<NodeProps> = (props) => {
	const { data } = props;
	const [label, setLabel] = useState(data.label || "");

	useEffect(() => {
		setLabel(data.label || "");
	}, [data.label]);

	// onRename callback pour ReactFlow
	const handleRename = (nodeId: string, newLabel: string) => {
		if (data.onRename) data.onRename(nodeId, newLabel);
		setLabel(newLabel);
	};

	return (
		<EditableNode
			{...props}
			data={{ ...data, label, onRename: handleRename }}
		/>
	);
};
