import { Check, Download, Palette, Plus, Trash2, Upload } from "lucide-react";
import { useCallback, useState } from "react";
import type { AppSettings } from "../../../shared/types";
import { cn } from "../../lib/utils";
import { useSettingsStore } from "../../stores/settings-store";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Separator } from "../ui/separator";

/**
 * Custom theme definition stored in settings
 */
export interface CustomThemeData {
	id: string;
	name: string;
	description: string;
	author: string;
	colors: {
		bg: string;
		accent: string;
		darkBg: string;
		darkAccent: string;
	};
	createdAt: string;
}

interface CustomThemeEditorProps {
	settings: AppSettings;
	onSettingsChange: (settings: AppSettings) => void;
}

const DEFAULT_CUSTOM_COLORS = {
	bg: "#F0F4F8",
	accent: "#3B82F6",
	darkBg: "#0F172A",
	darkAccent: "#60A5FA",
};

const COLOR_LABELS: Record<string, string> = {
	bg: "Light Background",
	accent: "Light Accent",
	darkBg: "Dark Background",
	darkAccent: "Dark Accent",
};

/**
 * Custom theme editor with color pickers, import/export, and per-project theme binding.
 * Feature 9.1 — Mode sombre/clair automatique + thème custom.
 */
export function CustomThemeEditor({
	settings,
	onSettingsChange,
}: CustomThemeEditorProps) {
	const updateStoreSettings = useSettingsStore((state) => state.updateSettings);
	const [isCreating, setIsCreating] = useState(false);
	const [editName, setEditName] = useState("");
	const [editDescription, setEditDescription] = useState("");
	const [editColors, setEditColors] = useState({ ...DEFAULT_CUSTOM_COLORS });
	const [importError, setImportError] = useState<string | null>(null);

	// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
	const customThemes: CustomThemeData[] = (settings as any).customThemes || [];

	const saveCustomThemes = useCallback(
		(themes: CustomThemeData[]) => {
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			const updated = { ...settings, customThemes: themes } as any;
			onSettingsChange(updated);
			// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
			updateStoreSettings({ customThemes: themes } as any);
		},
		[settings, onSettingsChange, updateStoreSettings],
	);

	const handleCreate = () => {
		if (!editName.trim()) return;

		const newTheme: CustomThemeData = {
			id: `custom-${Date.now()}`,
			name: editName.trim(),
			description: editDescription.trim(),
			author: "User",
			colors: { ...editColors },
			createdAt: new Date().toISOString(),
		};

		saveCustomThemes([...customThemes, newTheme]);
		setIsCreating(false);
		setEditName("");
		setEditDescription("");
		setEditColors({ ...DEFAULT_CUSTOM_COLORS });
	};

	const handleDelete = (themeId: string) => {
		saveCustomThemes(customThemes.filter((t) => t.id !== themeId));
	};

	const handleExport = (theme: CustomThemeData) => {
		const exportData = {
			...theme,
			_exportVersion: "1.0",
			_exportedAt: new Date().toISOString(),
		};
		const blob = new Blob([JSON.stringify(exportData, null, 2)], {
			type: "application/json",
		});
		const url = URL.createObjectURL(blob);
		const a = document.createElement("a");
		a.href = url;
		a.download = `theme-${theme.name.toLowerCase().replace(/\s+/g, "-")}.json`;
		a.click();
		URL.revokeObjectURL(url);
	};

	const handleImport = () => {
		setImportError(null);
		const input = document.createElement("input");
		input.type = "file";
		input.accept = ".json";
		input.onchange = async (e) => {
			const file = (e.target as HTMLInputElement).files?.[0];
			if (!file) return;

			try {
				const text = await file.text();
				const data = JSON.parse(text);

				if (
					!data.name ||
					!data.colors?.bg ||
					!data.colors?.accent ||
					!data.colors?.darkBg ||
					!data.colors?.darkAccent
				) {
					setImportError(
						"Invalid theme file: missing required fields (name, colors.bg, colors.accent, colors.darkBg, colors.darkAccent)",
					);
					return;
				}

				const imported: CustomThemeData = {
					id: `imported-${Date.now()}`,
					name: data.name,
					description: data.description || "",
					author: data.author || "Imported",
					colors: {
						bg: data.colors.bg,
						accent: data.colors.accent,
						darkBg: data.colors.darkBg,
						darkAccent: data.colors.darkAccent,
					},
					createdAt: new Date().toISOString(),
				};

				saveCustomThemes([...customThemes, imported]);
				setImportError(null);
			} catch {
				setImportError("Failed to parse theme file. Ensure it is valid JSON.");
			}
		};
		input.click();
	};

	const handleSelectCustomTheme = (themeId: string) => {
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		onSettingsChange({ ...settings, colorTheme: themeId as any });
		// biome-ignore lint/suspicious/noExplicitAny: TODO: type this properly
		updateStoreSettings({ colorTheme: themeId as any });
	};

	const currentColorTheme = settings.colorTheme || "default";
	const isDark =
		settings.theme === "dark" ||
		(settings.theme === "system" &&
			window.matchMedia("(prefers-color-scheme: dark)").matches);

	return (
		<div className="space-y-6">
			<Separator />

			{/* Custom Themes Section */}
			<div className="space-y-3">
				<div className="flex items-center justify-between">
					<div>
						<Label className="text-sm font-medium text-foreground">
							Custom Themes
						</Label>
						<p className="text-sm text-muted-foreground">
							Create your own color themes or import shared ones
						</p>
					</div>
					<div className="flex gap-2">
						<Button
							size="sm"
							variant="outline"
							onClick={handleImport}
							className="gap-1.5"
						>
							<Upload className="h-3.5 w-3.5" />
							Import
						</Button>
						<Button
							size="sm"
							variant="outline"
							onClick={() => setIsCreating(!isCreating)}
							className="gap-1.5"
						>
							<Plus className="h-3.5 w-3.5" />
							New Theme
						</Button>
					</div>
				</div>

				{importError && (
					<div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
						<p className="text-xs text-destructive">{importError}</p>
					</div>
				)}

				{/* Theme Creator */}
				{isCreating && (
					<div className="rounded-lg border border-primary/30 bg-primary/5 p-4 space-y-4">
						<div className="grid grid-cols-2 gap-3">
							<div className="space-y-1.5">
								<Label className="text-xs">Theme Name</Label>
								<Input
									value={editName}
									onChange={(e) => setEditName(e.target.value)}
									placeholder="My Custom Theme"
									className="h-8 text-sm"
								/>
							</div>
							<div className="space-y-1.5">
								<Label className="text-xs">Description</Label>
								<Input
									value={editDescription}
									onChange={(e) => setEditDescription(e.target.value)}
									placeholder="A brief description"
									className="h-8 text-sm"
								/>
							</div>
						</div>

						{/* Color Pickers */}
						<div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
							{(
								Object.keys(DEFAULT_CUSTOM_COLORS) as Array<
									keyof typeof DEFAULT_CUSTOM_COLORS
								>
							).map((key) => (
								<div key={key} className="space-y-1.5">
									<Label className="text-xs">{COLOR_LABELS[key]}</Label>
									<div className="flex items-center gap-2">
										<input
											type="color"
											value={editColors[key]}
											onChange={(e) =>
												setEditColors((prev) => ({
													...prev,
													[key]: e.target.value,
												}))
											}
											className="h-8 w-8 rounded border cursor-pointer"
										/>
										<Input
											value={editColors[key]}
											onChange={(e) =>
												setEditColors((prev) => ({
													...prev,
													[key]: e.target.value,
												}))
											}
											className="h-8 text-xs font-mono flex-1"
										/>
									</div>
								</div>
							))}
						</div>

						{/* Preview */}
						<div className="flex gap-2 items-center">
							<span className="text-xs text-muted-foreground">Preview:</span>
							<div className="flex -space-x-1">
								<div
									className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
									style={{ backgroundColor: editColors.bg }}
								/>
								<div
									className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
									style={{ backgroundColor: editColors.accent }}
								/>
								<div
									className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
									style={{ backgroundColor: editColors.darkBg }}
								/>
								<div
									className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
									style={{ backgroundColor: editColors.darkAccent }}
								/>
							</div>
						</div>

						<div className="flex gap-2 justify-end">
							<Button
								size="sm"
								variant="ghost"
								onClick={() => setIsCreating(false)}
							>
								Cancel
							</Button>
							<Button
								size="sm"
								onClick={handleCreate}
								disabled={!editName.trim()}
							>
								Create Theme
							</Button>
						</div>
					</div>
				)}

				{/* Custom Theme Cards */}
				{customThemes.length > 0 && (
					<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
						{customThemes.map((theme) => {
							const isSelected = currentColorTheme === theme.id;
							const bgColor = isDark ? theme.colors.darkBg : theme.colors.bg;
							const accentColor = isDark
								? theme.colors.darkAccent
								: theme.colors.accent;

							return (
								<div
									key={theme.id}
									className={cn(
										"relative flex flex-col p-4 rounded-lg border-2 text-left transition-all",
										"hover:shadow-md",
										isSelected
											? "border-primary bg-primary/5 shadow-sm"
											: "border-border hover:border-primary/50 hover:bg-accent/30",
									)}
								>
									{/* Selection indicator */}
									{isSelected && (
										<div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
											<Check className="w-3 h-3 text-primary-foreground" />
										</div>
									)}

									{/* Clickable area for selection */}
									<button
										type="button"
										onClick={() => handleSelectCustomTheme(theme.id)}
										className="text-left flex-1"
									>
										{/* Preview swatches */}
										<div className="flex items-center gap-2 mb-3">
											<div className="flex -space-x-1.5">
												<div
													className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
													style={{ backgroundColor: bgColor }}
												/>
												<div
													className="w-6 h-6 rounded-full border-2 border-background shadow-sm"
													style={{ backgroundColor: accentColor }}
												/>
											</div>
											<Palette className="h-3.5 w-3.5 text-muted-foreground ml-1" />
										</div>

										<div className="space-y-1">
											<p className="font-medium text-sm text-foreground">
												{theme.name}
											</p>
											{theme.description && (
												<p className="text-xs text-muted-foreground line-clamp-2">
													{theme.description}
												</p>
											)}
										</div>
									</button>

									{/* Actions */}
									<div className="flex gap-1 mt-3 pt-2 border-t border-border/50">
										<Button
											size="sm"
											variant="ghost"
											className="h-7 px-2 text-xs gap-1"
											onClick={() => handleExport(theme)}
										>
											<Download className="h-3 w-3" />
											Export
										</Button>
										<Button
											size="sm"
											variant="ghost"
											className="h-7 px-2 text-xs gap-1 text-destructive hover:text-destructive"
											onClick={() => handleDelete(theme.id)}
										>
											<Trash2 className="h-3 w-3" />
											Delete
										</Button>
									</div>
								</div>
							);
						})}
					</div>
				)}

				{customThemes.length === 0 && !isCreating && (
					<div className="rounded-lg border border-dashed border-border p-6 text-center">
						<Palette className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
						<p className="text-sm text-muted-foreground">
							No custom themes yet
						</p>
						<p className="text-xs text-muted-foreground mt-1">
							Create a new theme or import one to get started
						</p>
					</div>
				)}
			</div>
		</div>
	);
}
