import { useEffect, useState } from "react";

export const FolderExplorer = ({
	selectedFolder,
	setSelectedFolder,
}: {
	selectedFolder: string;
	setSelectedFolder: (folder: string) => void;
}) => {
	const [folders, setFolders] = useState<string[]>([]);
	const [currentPath, setCurrentPath] = useState<string>(selectedFolder);

	useEffect(() => {
		// Utilise File System Access API pour lister les dossiers
		async function fetchFolders() {
			if ("showDirectoryPicker" in window) {
				try {
					// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
					const dirHandle = await (window as any).showDirectoryPicker();
					setCurrentPath(dirHandle.name);
					const entries = [];
					for await (const entry of dirHandle.values()) {
						if (entry.kind === "directory") {
							entries.push(entry.name);
						}
					}
					setFolders(entries);
				} catch (_e) {
					setFolders([]);
				}
			} else {
				setFolders([]); // Fallback: rien
			}
		}
		fetchFolders();
	}, []);

	return (
		<div className="folder-explorer">
			<div className="current-path">{currentPath}</div>
			<ul>
				{folders.map((folder) => (
					<li key={folder}>
						<button
							type="button"
							className={selectedFolder === folder ? "selected" : ""}
							onClick={() => setSelectedFolder(folder)}
						>
							{folder}
						</button>
					</li>
				))}
			</ul>
		</div>
	);
};
