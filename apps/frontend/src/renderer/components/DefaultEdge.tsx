import type React from "react";
import { useState } from "react";
import {
	BaseEdge,
	EdgeLabelRenderer,
	type EdgeProps,
	getBezierPath,
} from "reactflow";

export const DefaultEdge: React.FC<EdgeProps> = (props) => {
	const {
		id,
		sourceX,
		sourceY,
		targetX,
		targetY,
		sourcePosition,
		targetPosition,
		style,
		markerEnd,
		data,
		selected,
	} = props;
	const [editing, setEditing] = useState(false);
	const [label, setLabel] = useState(data?.label || "");

	const [edgePath, labelX, labelY] = getBezierPath({
		sourceX,
		sourceY,
		sourcePosition,
		targetX,
		targetY,
		targetPosition,
	});

	const handleDoubleClick = () => setEditing(true);
	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) =>
		setLabel(e.target.value);
	const handleBlur = () => {
		setEditing(false);
		if (data?.onEdgeLabelChange) data.onEdgeLabelChange(id, label);
	};
	const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
		if (e.key === "Enter") {
			setEditing(false);
			if (data?.onEdgeLabelChange) data.onEdgeLabelChange(id, label);
		}
	};

	return (
		<>
			<BaseEdge path={edgePath} markerEnd={markerEnd} style={style} />
			<EdgeLabelRenderer>
				<div
					className="nodrag nopan"
					style={{
						position: "absolute",
						transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
						pointerEvents: "all",
						display: "flex",
						justifyContent: "center",
						alignItems: "center",
					}}
				>
					<button
						type="button"
						onDoubleClick={handleDoubleClick}
						onKeyDown={(e) => {
							if (e.key === "Enter" || e.key === " ") {
								e.preventDefault();
								handleDoubleClick();
							}
						}}
						style={{
							background: selected ? "#e0e7ff" : "#fff",
							borderRadius: 4,
							border: "1px solid #a5b4fc",
							padding: "2px 6px",
							minWidth: 40,
							minHeight: 20,
							fontSize: 13,
							cursor: "pointer",
						}}
					>
						{editing ? (
							<input
								value={label}
								onChange={handleChange}
								onBlur={handleBlur}
								onKeyDown={handleKeyDown}
								style={{
									width: 80,
									fontSize: 13,
									border: "1px solid #a5b4fc",
									borderRadius: 4,
									padding: 2,
								}}
							/>
						) : (
							<span>{label || "→"}</span>
						)}
					</button>
				</div>
			</EdgeLabelRenderer>
		</>
	);
};
