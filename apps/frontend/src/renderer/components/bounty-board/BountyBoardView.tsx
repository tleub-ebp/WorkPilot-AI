import { Plus, Swords, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useBountyBoardStore } from "../../stores/bounty-board-store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { ContestantCard } from "./ContestantCard";
import { JudgeVerdictModal } from "./JudgeVerdictModal";

interface Props {
	readonly projectPath?: string;
	readonly specId?: string;
}

export function BountyBoardView({ projectPath, specId }: Props) {
	const { t } = useTranslation(["bountyBoard", "common"]);
	const {
		contestants,
		current,
		archives,
		loading,
		error,
		addContestant,
		updateContestant,
		removeContestant,
		startBounty,
		loadArchives,
	} = useBountyBoardStore();

	const [projectInput, setProjectInput] = useState(projectPath ?? "");
	const [specInput, setSpecInput] = useState(specId ?? "");
	const [verdictOpen, setVerdictOpen] = useState(false);

	useEffect(() => {
		if (projectInput && specInput) {
			void loadArchives(projectInput, specInput);
		}
	}, [projectInput, specInput, loadArchives]);

	useEffect(() => {
		if (current?.status === "completed") {
			setVerdictOpen(true);
		}
	}, [current]);

	const canStart =
		!loading &&
		projectInput.trim() &&
		specInput.trim() &&
		contestants.length > 0;

	const handleStart = () => {
		if (!canStart) return;
		void startBounty(projectInput.trim(), specInput.trim());
	};

	return (
		<div className="flex flex-col gap-4 p-4">
			<header className="flex items-center gap-2">
				<Swords className="w-5 h-5" />
				<h2 className="text-lg font-semibold">
					{t("bountyBoard:title", "Bounty Board")}
				</h2>
			</header>

			<p className="text-sm text-muted-foreground">
				{t(
					"bountyBoard:description",
					"Run N contestants in parallel with different provider/model combinations. An impartial judge picks the winner.",
				)}
			</p>

			<section className="grid grid-cols-1 md:grid-cols-2 gap-2">
				<div>
					<Label className="text-xs">
						{t("bountyBoard:projectPath", "Project path")}
					</Label>
					<Input
						value={projectInput}
						onChange={(e) => setProjectInput(e.target.value)}
						placeholder="/path/to/repo"
					/>
				</div>
				<div>
					<Label className="text-xs">
						{t("bountyBoard:specId", "Spec id")}
					</Label>
					<Input
						value={specInput}
						onChange={(e) => setSpecInput(e.target.value)}
						placeholder="001-my-feature"
					/>
				</div>
			</section>

			<section className="space-y-2">
				<div className="flex items-center justify-between">
					<h3 className="text-sm font-semibold">
						{t("bountyBoard:contestants", "Contestants")}
					</h3>
					<Button
						size="sm"
						variant="outline"
						onClick={() =>
							addContestant({ provider: "anthropic", model: "claude-haiku-4-6" })
						}
					>
						<Plus className="w-3 h-3 mr-1" />
						{t("bountyBoard:addContestant", "Add contestant")}
					</Button>
				</div>

				<div className="space-y-2">
					{contestants.map((c, idx) => (
						<div
							key={`${c.provider}-${c.model}-${idx}`}
							className="grid grid-cols-12 gap-2 items-end border rounded-md p-2 bg-card"
						>
							<div className="col-span-4">
								<Label className="text-[10px]">
									{t("bountyBoard:field.provider", "Provider")}
								</Label>
								<Input
									value={c.provider}
									onChange={(e) =>
										updateContestant(idx, { provider: e.target.value })
									}
									placeholder="anthropic / openai / google / ollama / copilot / windsurf / custom"
								/>
							</div>
							<div className="col-span-4">
								<Label className="text-[10px]">
									{t("bountyBoard:field.model", "Model")}
								</Label>
								<Input
									value={c.model}
									onChange={(e) =>
										updateContestant(idx, { model: e.target.value })
									}
									placeholder="claude-sonnet-4-6"
								/>
							</div>
							<div className="col-span-3">
								<Label className="text-[10px]">
									{t("bountyBoard:field.profile", "Profile (optional)")}
								</Label>
								<Input
									value={c.profileId ?? ""}
									onChange={(e) =>
										updateContestant(idx, { profileId: e.target.value })
									}
								/>
							</div>
							<div className="col-span-1 flex justify-end">
								<Button
									size="icon"
									variant="ghost"
									onClick={() => removeContestant(idx)}
									disabled={contestants.length <= 1}
									aria-label={t("bountyBoard:remove", "Remove contestant")}
								>
									<Trash2 className="w-4 h-4" />
								</Button>
							</div>
						</div>
					))}
				</div>
			</section>

			<div className="flex gap-2">
				<Button onClick={handleStart} disabled={!canStart}>
					<Swords className="w-4 h-4 mr-1" />
					{loading
						? t("bountyBoard:running", "Running…")
						: t("bountyBoard:start", "Start bounty")}
				</Button>
			</div>

			{error && <p className="text-sm text-destructive">{error}</p>}

			{current && (
				<section>
					<h3 className="text-sm font-semibold mb-2">
						{t("bountyBoard:liveBoard", "Live board")}
					</h3>
					<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
						{current.contestants.map((c) => (
							<ContestantCard
								key={c.id}
								contestant={c}
								isWinner={c.id === current.winnerId}
								rationale={current.judgeRationale?.[c.id]}
							/>
						))}
					</div>
				</section>
			)}

			{archives.length > 0 && (
				<section>
					<h3 className="text-sm font-semibold mb-2">
						{t("bountyBoard:archives", "Previous rounds")}
					</h3>
					<ul className="text-xs space-y-1">
						{archives.slice(0, 10).map((a) => (
							<li key={a.id} className="flex gap-3 text-muted-foreground">
								<span className="font-mono">
									{new Date(a.createdAt).toLocaleString()}
								</span>
								<span>
									{t("bountyBoard:contestantsCount", {
										count: a.contestants.length,
										defaultValue: "{{count}} contestants",
									})}
								</span>
								<span>
									{a.winnerId
										? a.contestants.find((c) => c.id === a.winnerId)?.label
										: "—"}
								</span>
							</li>
						))}
					</ul>
				</section>
			)}

			{current && verdictOpen && (
				<JudgeVerdictModal result={current} onClose={() => setVerdictOpen(false)} />
			)}
		</div>
	);
}
