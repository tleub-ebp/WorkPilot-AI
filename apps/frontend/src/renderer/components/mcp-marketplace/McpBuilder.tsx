/**
 * MCP Builder — No-Code MCP Server Creator
 *
 * Visual interface for creating custom MCP servers without code.
 * Allows defining tools, parameters, and HTTP actions.
 */

import {
	ChevronRight,
	Code,
	Globe,
	Pencil,
	Plus,
	Save,
	Trash2,
	Wrench,
} from "lucide-react";
import { useCallback, useState } from "react";
import { useTranslation } from "react-i18next";
import type {
	McpBuilderActionType,
	McpBuilderParam,
	McpBuilderProject,
	McpBuilderTool,
} from "../../../shared/types/mcp-marketplace";
import {
	deleteBuilderProject,
	saveBuilderProject,
	useMcpMarketplaceStore,
} from "../../stores/mcp-marketplace-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { Textarea } from "../ui/textarea";

function generateId(): string {
	return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createEmptyTool(): McpBuilderTool {
	return {
		id: generateId(),
		name: "",
		description: "",
		parameters: [],
		action: {
			type: "http_request",
			http: {
				method: "GET",
				url: "",
			},
		},
	};
}

function createEmptyProject(): McpBuilderProject {
	return {
		id: generateId(),
		name: "",
		description: "",
		icon: "Wrench",
		color: "#6366F1",
		baseUrl: "",
		defaultHeaders: {},
		envVars: [],
		tools: [],
		createdAt: new Date().toISOString(),
		updatedAt: new Date().toISOString(),
	};
}

export function McpBuilder() {
	const { t } = useTranslation(["common"]);
	const { builderProjects, isBuilderLoading } = useMcpMarketplaceStore();

	const [selectedProjectId, setSelectedProjectId] = useState<string | null>(
		null,
	);
	const [editingProject, setEditingProject] =
		useState<McpBuilderProject | null>(null);
	const [editingToolId, setEditingToolId] = useState<string | null>(null);

	const handleNewProject = () => {
		const project = createEmptyProject();
		setEditingProject(project);
		setSelectedProjectId(project.id);
		setEditingToolId(null);
	};

	const handleSelectProject = (id: string) => {
		const project = builderProjects.find((p) => p.id === id);
		if (project) {
			setEditingProject({ ...project, tools: [...project.tools] });
			setSelectedProjectId(id);
			setEditingToolId(null);
		}
	};

	const handleSaveProject = async () => {
		if (!editingProject) return;
		editingProject.updatedAt = new Date().toISOString();
		const success = await saveBuilderProject(editingProject);
		if (success) {
			setSelectedProjectId(editingProject.id);
		}
	};

	const handleDeleteProject = async (id: string) => {
		await deleteBuilderProject(id);
		if (selectedProjectId === id) {
			setSelectedProjectId(null);
			setEditingProject(null);
		}
	};

	const updateProject = useCallback(
		(updates: Partial<McpBuilderProject>) => {
			if (!editingProject) return;
			setEditingProject({ ...editingProject, ...updates });
		},
		[editingProject],
	);

	const handleAddTool = () => {
		if (!editingProject) return;
		const tool = createEmptyTool();
		setEditingProject({
			...editingProject,
			tools: [...editingProject.tools, tool],
		});
		setEditingToolId(tool.id);
	};

	const handleRemoveTool = (toolId: string) => {
		if (!editingProject) return;
		setEditingProject({
			...editingProject,
			tools: editingProject.tools.filter((t) => t.id !== toolId),
		});
		if (editingToolId === toolId) setEditingToolId(null);
	};

	const handleUpdateTool = (
		toolId: string,
		updates: Partial<McpBuilderTool>,
	) => {
		if (!editingProject) return;
		setEditingProject({
			...editingProject,
			tools: editingProject.tools.map((t) =>
				t.id === toolId ? { ...t, ...updates } : t,
			),
		});
	};

	const handleAddParam = (toolId: string) => {
		if (!editingProject) return;
		const param: McpBuilderParam = {
			name: "",
			type: "string",
			description: "",
			required: true,
		};
		setEditingProject({
			...editingProject,
			tools: editingProject.tools.map((t) =>
				t.id === toolId ? { ...t, parameters: [...t.parameters, param] } : t,
			),
		});
	};

	const handleRemoveParam = (toolId: string, paramIndex: number) => {
		if (!editingProject) return;
		setEditingProject({
			...editingProject,
			tools: editingProject.tools.map((t) =>
				t.id === toolId
					? {
							...t,
							parameters: t.parameters.filter((_, i) => i !== paramIndex),
						}
					: t,
			),
		});
	};

	const handleUpdateParam = (
		toolId: string,
		paramIndex: number,
		updates: Partial<McpBuilderParam>,
	) => {
		if (!editingProject) return;
		setEditingProject({
			...editingProject,
			tools: editingProject.tools.map((t) =>
				t.id === toolId
					? {
							...t,
							parameters: t.parameters.map((p, i) =>
								i === paramIndex ? { ...p, ...updates } : p,
							),
						}
					: t,
			),
		});
	};

	const editingTool =
		editingProject?.tools.find((t) => t.id === editingToolId) || null;

	if (isBuilderLoading) {
		return (
			<div className="flex-1 flex items-center justify-center">
				<div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
			</div>
		);
	}

	return (
		<div className="flex-1 flex overflow-hidden">
			{/* Sidebar: project list */}
			<div className="w-64 shrink-0 border-r border-border bg-muted/20 flex flex-col">
				<div className="p-3 border-b border-border">
					<Button
						onClick={handleNewProject}
						className="w-full h-8 text-xs gap-1.5"
					>
						<Plus className="h-3.5 w-3.5" />
						{t("mcpMarketplace.builder.newProject")}
					</Button>
				</div>
				<div className="flex-1 overflow-auto p-2 space-y-1">
					{builderProjects.map((project) => (
						<button
							type="button"
							key={project.id}
							onClick={() => handleSelectProject(project.id)}
							className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center gap-2 ${
								selectedProjectId === project.id
									? "bg-primary/10 text-primary font-medium"
									: "hover:bg-muted text-foreground"
							}`}
						>
							<div
								className="w-5 h-5 rounded shrink-0 flex items-center justify-center text-white text-[10px] font-bold"
								style={{ backgroundColor: project.color }}
							>
								{project.name?.charAt(0) || "?"}
							</div>
							<span className="truncate">
								{project.name || t("mcpMarketplace.builder.untitled")}
							</span>
						</button>
					))}
					{builderProjects.length === 0 && !editingProject && (
						<p className="text-xs text-muted-foreground text-center py-8 px-3">
							{t("mcpMarketplace.builder.emptyHint")}
						</p>
					)}
				</div>
			</div>

			{/* Main editor area */}
			{editingProject ? (
				<div className="flex-1 flex flex-col overflow-hidden">
					{/* Project header bar */}
					<div className="shrink-0 flex items-center justify-between px-5 py-3 border-b border-border bg-background">
						<div className="flex items-center gap-3">
							<div
								className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold"
								style={{ backgroundColor: editingProject.color }}
							>
								{editingProject.name?.charAt(0) || "?"}
							</div>
							<div>
								<h2 className="font-medium text-sm">
									{editingProject.name || t("mcpMarketplace.builder.untitled")}
								</h2>
								<p className="text-xs text-muted-foreground">
									{editingProject.tools.length}{" "}
									{t("mcpMarketplace.builder.tools")}
								</p>
							</div>
						</div>
						<div className="flex items-center gap-2">
							<Button
								variant="outline"
								size="sm"
								onClick={() => handleDeleteProject(editingProject.id)}
							>
								<Trash2 className="h-3.5 w-3.5 mr-1.5" />
								{t("common:delete")}
							</Button>
							<Button size="sm" onClick={handleSaveProject}>
								<Save className="h-3.5 w-3.5 mr-1.5" />
								{t("common:save")}
							</Button>
						</div>
					</div>

					{/* Two-column layout: tools list + tool editor */}
					<div className="flex-1 flex overflow-hidden">
						{/* Left: project config + tools list */}
						<div className="w-80 shrink-0 border-r border-border overflow-auto p-4 space-y-5">
							{/* Project details */}
							<div className="space-y-3">
								<h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
									{t("mcpMarketplace.builder.serverConfig")}
								</h3>
								<div className="space-y-2">
									<div>
										<Label className="text-xs">
											{t("mcpMarketplace.builder.serverName")}
										</Label>
										<Input
											value={editingProject.name}
											onChange={(e) => updateProject({ name: e.target.value })}
											placeholder="My Custom Server"
											className="h-8 text-sm mt-1"
										/>
									</div>
									<div>
										<Label className="text-xs">
											{t("mcpMarketplace.builder.description")}
										</Label>
										<Textarea
											value={editingProject.description}
											onChange={(e) =>
												updateProject({ description: e.target.value })
											}
											placeholder="What does this server do?"
											className="text-sm mt-1 min-h-[60px]"
										/>
									</div>
									<div>
										<Label className="text-xs">
											{t("mcpMarketplace.builder.baseUrl")}
										</Label>
										<Input
											value={editingProject.baseUrl || ""}
											onChange={(e) =>
												updateProject({ baseUrl: e.target.value })
											}
											placeholder="https://api.example.com"
											className="h-8 text-sm mt-1"
										/>
									</div>
									<div>
										<Label className="text-xs">
											{t("mcpMarketplace.builder.color")}
										</Label>
										<div className="flex gap-2 mt-1">
											<input
												type="color"
												value={editingProject.color}
												onChange={(e) =>
													updateProject({ color: e.target.value })
												}
												className="w-8 h-8 rounded border border-border cursor-pointer"
											/>
											<Input
												value={editingProject.color}
												onChange={(e) =>
													updateProject({ color: e.target.value })
												}
												className="h-8 text-sm flex-1"
											/>
										</div>
									</div>
								</div>
							</div>

							{/* Tools list */}
							<div className="space-y-2">
								<div className="flex items-center justify-between">
									<h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
										{t("mcpMarketplace.builder.tools")}
									</h3>
									<Button
										variant="ghost"
										size="icon"
										className="h-6 w-6"
										onClick={handleAddTool}
									>
										<Plus className="h-3.5 w-3.5" />
									</Button>
								</div>
								{editingProject.tools.length === 0 ? (
									<p className="text-xs text-muted-foreground py-4 text-center">
										{t("mcpMarketplace.builder.noTools")}
									</p>
								) : (
									<div className="space-y-1">
										{editingProject.tools.map((tool) => (
											<button
												type="button"
												key={tool.id}
												onClick={() => setEditingToolId(tool.id)}
												className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
													editingToolId === tool.id
														? "bg-primary/10 text-primary"
														: "hover:bg-muted"
												}`}
											>
												<Code className="h-3.5 w-3.5 shrink-0" />
												<span className="truncate flex-1">
													{tool.name ||
														t("mcpMarketplace.builder.untitledTool")}
												</span>
												<Badge variant="secondary" className="text-[9px] px-1">
													{tool.action.type === "http_request"
														? "HTTP"
														: tool.action.type}
												</Badge>
												<ChevronRight className="h-3 w-3 shrink-0 opacity-40" />
											</button>
										))}
									</div>
								)}
							</div>
						</div>

						{/* Right: tool editor */}
						<div className="flex-1 overflow-auto p-5">
							{editingTool ? (
								<div className="max-w-2xl space-y-5">
									<div className="flex items-center justify-between">
										<h3 className="font-medium text-sm flex items-center gap-2">
											<Pencil className="h-4 w-4 text-primary" />
											{t("mcpMarketplace.builder.editTool")}
										</h3>
										<Button
											variant="ghost"
											size="sm"
											className="text-destructive hover:text-destructive"
											onClick={() => handleRemoveTool(editingTool.id)}
										>
											<Trash2 className="h-3.5 w-3.5 mr-1" />
											{t("mcpMarketplace.builder.removeTool")}
										</Button>
									</div>

									{/* Tool name + description */}
									<div className="grid grid-cols-2 gap-3">
										<div>
											<Label className="text-xs">
												{t("mcpMarketplace.builder.toolName")}
											</Label>
											<Input
												value={editingTool.name}
												onChange={(e) =>
													handleUpdateTool(editingTool.id, {
														name: e.target.value,
													})
												}
												placeholder="get_users"
												className="h-8 text-sm mt-1 font-mono"
											/>
										</div>
										<div>
											<Label className="text-xs">
												{t("mcpMarketplace.builder.toolDescription")}
											</Label>
											<Input
												value={editingTool.description}
												onChange={(e) =>
													handleUpdateTool(editingTool.id, {
														description: e.target.value,
													})
												}
												placeholder="Retrieve a list of users"
												className="h-8 text-sm mt-1"
											/>
										</div>
									</div>

									{/* Action type */}
									<div>
										<Label className="text-xs">
											{t("mcpMarketplace.builder.actionType")}
										</Label>
										<Select
											value={editingTool.action.type}
											onValueChange={(val) =>
												handleUpdateTool(editingTool.id, {
													action: {
														...editingTool.action,
														type: val as McpBuilderActionType,
													},
												})
											}
										>
											<SelectTrigger className="h-8 text-sm mt-1">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectItem value="http_request">
													<span className="flex items-center gap-1.5">
														<Globe className="h-3.5 w-3.5" />
														HTTP Request
													</span>
												</SelectItem>
												<SelectItem value="transform">
													<span className="flex items-center gap-1.5">
														<Code className="h-3.5 w-3.5" />
														Transform
													</span>
												</SelectItem>
											</SelectContent>
										</Select>
									</div>

									{/* HTTP action config */}
									{editingTool.action.type === "http_request" && (
										<div className="space-y-3 p-3 rounded-lg border border-border bg-muted/20">
											<h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
												<Globe className="h-3.5 w-3.5" />
												HTTP Configuration
											</h4>
											<div className="flex gap-2">
												<Select
													value={editingTool.action.http?.method || "GET"}
													onValueChange={(val) =>
														handleUpdateTool(editingTool.id, {
															action: {
																...editingTool.action,
																http: editingTool.action.http
																	? {
																			...editingTool.action.http,
																			method: val as
																				| "GET"
																				| "POST"
																				| "PUT"
																				| "PATCH"
																				| "DELETE",
																		}
																	: {
																			method: val as
																				| "GET"
																				| "POST"
																				| "PUT"
																				| "PATCH"
																				| "DELETE",
																			url: "",
																		},
															},
														})
													}
												>
													<SelectTrigger className="w-28 h-8 text-sm">
														<SelectValue />
													</SelectTrigger>
													<SelectContent>
														{(
															["GET", "POST", "PUT", "PATCH", "DELETE"] as const
														).map((m) => (
															<SelectItem key={m} value={m}>
																{m}
															</SelectItem>
														))}
													</SelectContent>
												</Select>
												<Input
													value={editingTool.action.http?.url || ""}
													onChange={(e) =>
														handleUpdateTool(editingTool.id, {
															action: {
																...editingTool.action,
																http: editingTool.action.http
																	? {
																			...editingTool.action.http,
																			url: e.target.value,
																		}
																	: {
																			method: "GET",
																			url: e.target.value,
																		},
															},
														})
													}
													placeholder="/api/users"
													className="h-8 text-sm flex-1 font-mono"
												/>
											</div>
											<div>
												<Label className="text-xs">
													{t("mcpMarketplace.builder.bodyTemplate")}
												</Label>
												<Textarea
													value={editingTool.action.http?.bodyTemplate || ""}
													onChange={(e) =>
														handleUpdateTool(editingTool.id, {
															action: {
																...editingTool.action,
																http: editingTool.action.http
																	? {
																			...editingTool.action.http,
																			bodyTemplate: e.target.value,
																		}
																	: {
																			method: "GET",
																			url: "",
																			bodyTemplate: e.target.value,
																		},
															},
														})
													}
													placeholder='{"name": "{{name}}", "email": "{{email}}"}'
													className="text-xs font-mono mt-1 min-h-[80px]"
												/>
											</div>
										</div>
									)}

									{/* Transform action config */}
									{editingTool.action.type === "transform" && (
										<div className="space-y-3 p-3 rounded-lg border border-border bg-muted/20">
											<h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
												<Code className="h-3.5 w-3.5" />
												Transform Template
											</h4>
											<Textarea
												value={editingTool.action.transform?.template || ""}
												onChange={(e) =>
													handleUpdateTool(editingTool.id, {
														action: {
															...editingTool.action,
															transform: { template: e.target.value },
														},
													})
												}
												placeholder="Template for transforming input data..."
												className="text-xs font-mono min-h-[100px]"
											/>
										</div>
									)}

									{/* Parameters */}
									<div className="space-y-3">
										<div className="flex items-center justify-between">
											<h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
												{t("mcpMarketplace.builder.parameters")}
											</h4>
											<Button
												variant="outline"
												size="sm"
												className="h-7 text-xs gap-1"
												onClick={() => handleAddParam(editingTool.id)}
											>
												<Plus className="h-3 w-3" />
												{t("mcpMarketplace.builder.addParam")}
											</Button>
										</div>

										{editingTool.parameters.length === 0 ? (
											<p className="text-xs text-muted-foreground text-center py-3">
												{t("mcpMarketplace.builder.noParams")}
											</p>
										) : (
											<div className="space-y-2">
												{editingTool.parameters.map((param, idx) => (
													<div
														key={`${editingTool.id}-param-${idx}`}
														className="flex items-start gap-2 p-2 rounded-lg border border-border bg-background"
													>
														<div className="grid grid-cols-3 gap-2 flex-1">
															<Input
																value={param.name}
																onChange={(e) =>
																	handleUpdateParam(editingTool.id, idx, {
																		name: e.target.value,
																	})
																}
																placeholder="param_name"
																className="h-7 text-xs font-mono"
															/>
															<Select
																value={param.type}
																onValueChange={(val) =>
																	handleUpdateParam(editingTool.id, idx, {
																		type: val as McpBuilderParam["type"],
																	})
																}
															>
																<SelectTrigger className="h-7 text-xs">
																	<SelectValue />
																</SelectTrigger>
																<SelectContent>
																	{[
																		"string",
																		"number",
																		"boolean",
																		"array",
																		"object",
																	].map((type) => (
																		<SelectItem key={type} value={type}>
																			{type}
																		</SelectItem>
																	))}
																</SelectContent>
															</Select>
															<Input
																value={param.description}
																onChange={(e) =>
																	handleUpdateParam(editingTool.id, idx, {
																		description: e.target.value,
																	})
																}
																placeholder="Description"
																className="h-7 text-xs"
															/>
														</div>
														<Button
															variant="ghost"
															size="icon"
															className="h-7 w-7 shrink-0 text-muted-foreground hover:text-destructive"
															onClick={() =>
																handleRemoveParam(editingTool.id, idx)
															}
														>
															<Trash2 className="h-3 w-3" />
														</Button>
													</div>
												))}
											</div>
										)}
									</div>
								</div>
							) : (
								<div className="flex flex-col items-center justify-center h-full text-muted-foreground">
									<Wrench className="h-12 w-12 mb-3 opacity-20" />
									<p className="text-sm">
										{t("mcpMarketplace.builder.selectTool")}
									</p>
								</div>
							)}
						</div>
					</div>
				</div>
			) : (
				<div className="flex-1 flex flex-col items-center justify-center text-muted-foreground px-6">
					<Wrench className="h-16 w-16 mb-4 opacity-20" />
					<h2 className="text-lg font-medium mb-1">
						{t("mcpMarketplace.builder.welcome")}
					</h2>
					<p className="text-sm text-center max-w-md mb-4">
						{t("mcpMarketplace.builder.welcomeHint")}
					</p>
					<Button onClick={handleNewProject} className="gap-1.5">
						<Plus className="h-4 w-4" />
						{t("mcpMarketplace.builder.newProject")}
					</Button>
				</div>
			)}
		</div>
	);
}
