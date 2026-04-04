import type { RepoTarget } from "@shared/types";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMultiRepoStore } from "@/stores/multi-repo-store";

/**
 * RepoSelector - Add/remove/configure target repositories for multi-repo orchestration
 */
export function RepoSelector() {
	const { t } = useTranslation(["multiRepo", "common"]);
	// biome-ignore lint/correctness/noUnusedVariables: variable kept for clarity
	const { targetRepos, addRepo, removeRepo, updateRepo } = useMultiRepoStore();
	const [repoInput, setRepoInput] = useState("");
	const [pathInput, setPathInput] = useState("");

	const handleAddRepo = () => {
		if (!repoInput.trim() || !pathInput.trim()) return;

		const id = repoInput.replace(/[^\w-]/g, "_") + "_" + Date.now();
		const newRepo: RepoTarget = {
			id,
			repo: repoInput.trim(),
			displayName: repoInput.trim().split("/").pop() || repoInput.trim(),
			localPath: pathInput.trim(),
		};

		addRepo(newRepo);
		setRepoInput("");
		setPathInput("");
	};

	const handleBrowse = async () => {
		try {
			const result = await window.electronAPI.selectDirectory();
			if (result) {
				setPathInput(result);
				if (!repoInput.trim()) {
					// Auto-fill repo name from directory name
					const dirName = result.split(/[\\/]/).pop() || "";
					setRepoInput(dirName);
				}
			}
		} catch {
			// User cancelled
		}
	};

	const handleKeyDown = (e: React.KeyboardEvent) => {
		if (e.key === "Enter") {
			e.preventDefault();
			handleAddRepo();
		}
	};

	return (
		<div className="space-y-4">
			{/* Add repo form */}
			<div className="flex flex-col gap-2">
				<div className="flex gap-2">
					<input
						type="text"
						value={repoInput}
						onChange={(e) => setRepoInput(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder={t("multiRepo:dialog.repoNamePlaceholder")}
						className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
					/>
				</div>
				<div className="flex gap-2">
					<input
						type="text"
						value={pathInput}
						onChange={(e) => setPathInput(e.target.value)}
						onKeyDown={handleKeyDown}
						placeholder={t("multiRepo:dialog.repoPathPlaceholder")}
						className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
					/>
					<button
						type="button"
						onClick={handleBrowse}
						className="rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground hover:bg-accent transition-colors"
					>
						{t("common:browse")}
					</button>
					<button
						type="button"
						onClick={handleAddRepo}
						disabled={!repoInput.trim() || !pathInput.trim()}
						className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					>
						{t("multiRepo:dialog.addRepo")}
					</button>
				</div>
			</div>

			{/* Repo list */}
			{targetRepos.length > 0 && (
				<div className="space-y-2">
					{targetRepos.map((repo, index) => (
						<div
							key={repo.id}
							className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
						>
							<div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
								{index + 1}
							</div>
							<div className="flex-1 min-w-0">
								<div className="font-medium text-sm text-foreground truncate">
									{repo.repo}
								</div>
								<div className="text-xs text-muted-foreground truncate">
									{repo.localPath}
								</div>
							</div>
							<button
								type="button"
								onClick={() => removeRepo(repo.id)}
								className="rounded-md p-1 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
								title={t("multiRepo:dialog.removeRepo")}
							>
								{/* biome-ignore lint/a11y/noSvgWithoutTitle: SVG is decorative, intentional  */}
								<svg
									className="h-4 w-4"
									fill="none"
									viewBox="0 0 24 24"
									strokeWidth={1.5}
									stroke="currentColor"
								>
									<path
										strokeLinecap="round"
										strokeLinejoin="round"
										d="M6 18L18 6M6 6l12 12"
									/>
								</svg>
							</button>
						</div>
					))}
				</div>
			)}

			{targetRepos.length === 0 && (
				<div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
					{t("multiRepo:dialog.noReposAdded")}
				</div>
			)}
		</div>
	);
}
