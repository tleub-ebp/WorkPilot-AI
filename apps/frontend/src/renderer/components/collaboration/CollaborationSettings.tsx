/**
 * CollaborationSettings — Settings panel for multi-user collaboration.
 *
 * Configures conflict resolution strategy, presence indicators,
 * chat settings, and notification preferences.
 *
 * Feature 3.1 — Mode multi-utilisateurs en temps réel.
 */

import { Users } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "../../lib/utils";
import {
	type ConflictResolution,
	useCollaborationStore,
} from "../../stores/collaboration-store";
import { Label } from "../ui/label";
import { Separator } from "../ui/separator";
import { Switch } from "../ui/switch";

const CONFLICT_STRATEGIES: {
	value: ConflictResolution;
	labelKey: string;
	descKey: string;
}[] = [
	{
		value: "last_write_wins",
		labelKey: "settings.conflictStrategy.lastWriteWins",
		descKey: "settings.conflictStrategy.lastWriteWinsDesc",
	},
	{
		value: "first_write_wins",
		labelKey: "settings.conflictStrategy.firstWriteWins",
		descKey: "settings.conflictStrategy.firstWriteWinsDesc",
	},
	{
		value: "manual",
		labelKey: "settings.conflictStrategy.manual",
		descKey: "settings.conflictStrategy.manualDesc",
	},
	{
		value: "merge",
		labelKey: "settings.conflictStrategy.merge",
		descKey: "settings.conflictStrategy.mergeDesc",
	},
];

export function CollaborationSettings() {
	const { t } = useTranslation("collaboration");
	const settings = useCollaborationStore((s) => s.settings);
	const updateSettings = useCollaborationStore((s) => s.updateSettings);

	return (
		<div className="space-y-6">
			{/* Header */}
			<div className="flex items-center gap-3">
				<div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
					<Users className="h-5 w-5 text-primary" />
				</div>
				<div>
					<h3 className="text-base font-semibold">{t("settings.title")}</h3>
					<p className="text-sm text-muted-foreground">
						{t("settings.description")}
					</p>
				</div>
			</div>

			<Separator />

			{/* Conflict Resolution Strategy */}
			<div className="space-y-3">
				<div>
					<Label className="text-sm font-medium">
						{t("settings.conflictStrategy.title")}
					</Label>
					<p className="text-xs text-muted-foreground mt-0.5">
						{t("settings.conflictStrategy.description")}
					</p>
				</div>
				<div className="grid grid-cols-2 gap-2">
					{CONFLICT_STRATEGIES.map((strategy) => (
						<button
							type="button"
							key={strategy.value}
							onClick={() =>
								updateSettings({ conflictStrategy: strategy.value })
							}
							className={cn(
								"rounded-lg border-2 p-3 text-left transition-all",
								"focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
								settings.conflictStrategy === strategy.value
									? "border-primary bg-primary/5"
									: "border-border hover:border-primary/50 hover:bg-accent/50",
							)}
						>
							<div className="text-sm font-medium">{t(strategy.labelKey)}</div>
							<div className="text-xs text-muted-foreground mt-0.5">
								{t(strategy.descKey)}
							</div>
						</button>
					))}
				</div>
			</div>

			<Separator />

			{/* Presence Indicator */}
			<div className="space-y-3">
				<div>
					<Label className="text-sm font-medium">
						{t("settings.presenceIndicator.title")}
					</Label>
					<p className="text-xs text-muted-foreground mt-0.5">
						{t("settings.presenceIndicator.description")}
					</p>
				</div>
				<div className="flex items-center justify-between">
					<Label className="text-sm">
						{t("settings.presenceIndicator.enabled")}
					</Label>
					<Switch
						checked={settings.showPresenceIndicator}
						onCheckedChange={(checked) =>
							updateSettings({ showPresenceIndicator: checked })
						}
					/>
				</div>
			</div>

			<Separator />

			{/* Chat Settings */}
			<div className="space-y-3">
				<div>
					<Label className="text-sm font-medium">
						{t("settings.chat.title")}
					</Label>
					<p className="text-xs text-muted-foreground mt-0.5">
						{t("settings.chat.description")}
					</p>
				</div>
				<div className="space-y-3">
					<div className="flex items-center justify-between">
						<Label className="text-sm">{t("settings.chat.enabled")}</Label>
						<Switch
							checked={settings.chatEnabled}
							onCheckedChange={(checked) =>
								updateSettings({ chatEnabled: checked })
							}
						/>
					</div>
					<div className="flex items-center justify-between">
						<Label className="text-sm">
							{t("settings.chat.soundNotifications")}
						</Label>
						<Switch
							checked={settings.chatSoundNotifications}
							onCheckedChange={(checked) =>
								updateSettings({ chatSoundNotifications: checked })
							}
							disabled={!settings.chatEnabled}
						/>
					</div>
					<div className="flex items-center justify-between">
						<Label className="text-sm">
							{t("settings.chat.desktopNotifications")}
						</Label>
						<Switch
							checked={settings.chatDesktopNotifications}
							onCheckedChange={(checked) =>
								updateSettings({ chatDesktopNotifications: checked })
							}
							disabled={!settings.chatEnabled}
						/>
					</div>
				</div>
			</div>

			<Separator />

			{/* Notification Preferences */}
			<div className="space-y-3">
				<div>
					<Label className="text-sm font-medium">
						{t("settings.notifications.title")}
					</Label>
					<p className="text-xs text-muted-foreground mt-0.5">
						{t("settings.notifications.description")}
					</p>
				</div>
				<div className="space-y-3">
					<div className="flex items-center justify-between">
						<Label className="text-sm">
							{t("settings.notifications.userJoinLeave")}
						</Label>
						<Switch
							checked={settings.notifyUserJoinLeave}
							onCheckedChange={(checked) =>
								updateSettings({ notifyUserJoinLeave: checked })
							}
						/>
					</div>
					<div className="flex items-center justify-between">
						<Label className="text-sm">
							{t("settings.notifications.taskLocks")}
						</Label>
						<Switch
							checked={settings.notifyTaskLocks}
							onCheckedChange={(checked) =>
								updateSettings({ notifyTaskLocks: checked })
							}
						/>
					</div>
					<div className="flex items-center justify-between">
						<Label className="text-sm">
							{t("settings.notifications.agentActivity")}
						</Label>
						<Switch
							checked={settings.notifyAgentActivity}
							onCheckedChange={(checked) =>
								updateSettings({ notifyAgentActivity: checked })
							}
						/>
					</div>
					<div className="flex items-center justify-between">
						<Label className="text-sm">
							{t("settings.notifications.chatMentions")}
						</Label>
						<Switch
							checked={settings.notifyChatMentions}
							onCheckedChange={(checked) =>
								updateSettings({ notifyChatMentions: checked })
							}
						/>
					</div>
					<div className="flex items-center justify-between">
						<Label className="text-sm">
							{t("settings.notifications.conflicts")}
						</Label>
						<Switch
							checked={settings.notifyConflicts}
							onCheckedChange={(checked) =>
								updateSettings({ notifyConflicts: checked })
							}
						/>
					</div>
				</div>
			</div>
		</div>
	);
}
