import type React from "react";
import { useState } from "react";
import type { FileDiff } from "../../../shared/types/sandbox";

interface DiffPreviewProps {
	readonly diffs: FileDiff[];
	readonly onFileSelect?: (filePath: string) => void;
}

const CHANGE_ICON: Record<string, string> = {
	added: "A",
	modified: "M",
	deleted: "D",
	renamed: "R",
};

const CHANGE_COLORS: Record<string, string> = {
	added: "text-green-400",
	modified: "text-blue-400",
	deleted: "text-red-400",
	renamed: "text-purple-400",
};

export function DiffPreview({
	diffs,
	onFileSelect,
}: DiffPreviewProps): React.ReactElement {
	const [selectedFile, setSelectedFile] = useState<string | null>(
		diffs[0]?.filePath ?? null,
	);

	const activeDiff = diffs.find((d) => d.filePath === selectedFile);

	const totalAdditions = diffs.reduce((sum, d) => sum + d.additions, 0);
	const totalDeletions = diffs.reduce((sum, d) => sum + d.deletions, 0);

	function handleSelect(filePath: string) {
		setSelectedFile(filePath);
		onFileSelect?.(filePath);
	}

	return (
		<div className="flex h-full bg-(--bg-primary) text-(--text-primary)">
			{/* File list sidebar */}
			<div className="w-64 border-r border-(--border-color) overflow-y-auto">
				<div className="px-3 py-2 border-b border-(--border-color)">
					<p className="text-xs text-(--text-secondary)">
						{diffs.length} files changed
					</p>
					<p className="text-xs">
						<span className="text-green-400">+{totalAdditions}</span>
						{" / "}
						<span className="text-red-400">-{totalDeletions}</span>
					</p>
				</div>
				{diffs.map((diff) => (
					<button
						key={diff.filePath}
						type="button"
						onClick={() => handleSelect(diff.filePath)}
						className={`w-full text-left px-3 py-2 text-xs hover:bg-(--bg-secondary) flex items-center gap-2 transition-colors ${
							diff.filePath === selectedFile
								? "bg-(--bg-secondary)"
								: ""
						}`}
					>
						<span
							className={`font-mono font-bold ${CHANGE_COLORS[diff.changeType] ?? ""}`}
						>
							{CHANGE_ICON[diff.changeType] ?? "?"}
						</span>
						<span className="truncate font-mono">
							{diff.filePath.split("/").pop()}
						</span>
						<span className="ml-auto text-green-400">
							+{diff.additions}
						</span>
						<span className="text-red-400">-{diff.deletions}</span>
					</button>
				))}
			</div>

			{/* Diff content */}
			<div className="flex-1 overflow-y-auto">
				{activeDiff ? (
					<div className="p-4">
						<div className="flex items-center gap-2 mb-3">
							<span
								className={`font-mono font-bold text-sm ${CHANGE_COLORS[activeDiff.changeType] ?? ""}`}
							>
								{CHANGE_ICON[activeDiff.changeType]}
							</span>
							<span className="font-mono text-sm">
								{activeDiff.filePath}
							</span>
						</div>
						<div className="space-y-2">
							{activeDiff.hunks.map((hunk, idx) => (
								<div
									key={`${activeDiff.filePath}-hunk-${hunk.oldStart}-${hunk.oldCount}-${hunk.newStart}-${hunk.newCount}`}
									className="rounded-lg border border-(--border-color) overflow-hidden"
								>
									<div className="px-3 py-1 text-xs bg-(--bg-secondary) text-(--text-secondary) font-mono">
										@@ -{hunk.oldStart},{hunk.oldCount} +
										{hunk.newStart},{hunk.newCount} @@
									</div>
									<pre className="px-3 py-2 text-xs font-mono leading-5 overflow-x-auto">
										{hunk.content.split("\n").map((line) => {
											let lineClass: string;
											if (line.startsWith("+")) {
												lineClass = "bg-green-500/10 text-green-300";
											} else if (line.startsWith("-")) {
												lineClass = "bg-red-500/10 text-red-300";
											} else {
												lineClass = "text-[var(--text-secondary)]";
											}
											return (
												<div
													key={line}
													className={lineClass}
												>
													{line}
												</div>
											);
										})}
									</pre>
								</div>
							))}
						</div>
					</div>
				) : (
					<div className="flex items-center justify-center h-full text-(--text-secondary)">
						Select a file to view the diff
					</div>
				)}
			</div>
		</div>
	);
}
