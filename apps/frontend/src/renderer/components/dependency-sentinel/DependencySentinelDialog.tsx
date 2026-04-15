import {
	AlertTriangle,
	CheckCircle,
	Loader2,
	Package,
	RefreshCw,
	Search,
	Shield,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDependencySentinelStore } from "../../stores/dependency-sentinel-store";
import { useProjectStore } from "../../stores/project-store";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "../ui/card";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "../ui/dialog";
import { Input } from "../ui/input";
import { ScrollArea } from "../ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";

interface Dependency {
	name: string;
	version: string;
	type: "production" | "development" | "peer";
	status: "secure" | "vulnerable" | "outdated" | "unknown";
	severity?: "low" | "medium" | "high" | "critical";
	description?: string;
	recommendation?: string;
}

interface Vulnerability {
	id: string;
	title: string;
	severity: "low" | "medium" | "high" | "critical";
	package: string;
	version: string;
	description: string;
	recommendation: string;
	cve?: string;
}

const STATUS_COLORS = {
	secure: "bg-green-100 text-green-800",
	vulnerable: "bg-red-100 text-red-800",
	outdated: "bg-yellow-100 text-yellow-800",
	unknown: "bg-gray-100 text-gray-800",
};

const SEVERITY_COLORS = {
	low: "bg-blue-100 text-blue-800",
	medium: "bg-yellow-100 text-yellow-800",
	high: "bg-orange-100 text-orange-800",
	critical: "bg-red-100 text-red-800",
};

/**
 * DependencySentinelDialog — AI-powered dependency monitoring dialog.
 *
 * Shows a dialog where users can analyze their project dependencies for
 * security vulnerabilities, outdated packages, and compatibility issues.
 */
export function DependencySentinelDialog() {
	const { t } = useTranslation(["dialogs", "common"]);
	const { isOpen, closeDialog } = useDependencySentinelStore();
	const selectedProject = useProjectStore((state) =>
		state.projects.find((p) => p.id === state.selectedProjectId),
	);

	const [dependencies, setDependencies] = useState<Dependency[]>([]);
	const [vulnerabilities, setVulnerabilities] = useState<Vulnerability[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [searchQuery, setSearchQuery] = useState("");
	const [activeTab, setActiveTab] = useState("dependencies");

	// Mock data for demonstration
	const mockDependencies: Dependency[] = [
		{
			name: "react",
			version: "18.2.0",
			type: "production",
			status: "secure",
			description:
				"React is a JavaScript library for building user interfaces.",
		},
		{
			name: "axios",
			version: "1.4.0",
			type: "production",
			status: "vulnerable",
			severity: "medium",
			description: "Promise based HTTP client for the browser and node.js.",
			recommendation: "Update to version 1.6.0 or later",
		},
		{
			name: "typescript",
			version: "5.0.0",
			type: "development",
			status: "outdated",
			description: "TypeScript is a language for application-scale JavaScript.",
			recommendation: "Update to version 5.2.0 or later",
		},
	];

	const mockVulnerabilities: Vulnerability[] = [
		{
			id: "VULN-001",
			title: "Prototype Pollution in Axios",
			severity: "medium",
			package: "axios",
			version: "1.4.0",
			description:
				"Axios versions before 1.6.0 are vulnerable to prototype pollution.",
			recommendation: "Update to axios 1.6.0 or later",
			cve: "CVE-2023-45678",
		},
	];

	const loadDependencies = useCallback(async () => {
		if (!selectedProject) return;

		setIsLoading(true);
		try {
			// In a real implementation, this would call the backend API
			// For now, we'll use mock data
			await new Promise((resolve) => setTimeout(resolve, 1000));
			setDependencies(mockDependencies);
			setVulnerabilities(mockVulnerabilities);
		} catch (error) {
			console.error("Failed to load dependencies:", error);
		} finally {
			setIsLoading(false);
		}
	}, [selectedProject, mockVulnerabilities, mockDependencies]);

	useEffect(() => {
		if (isOpen && selectedProject) {
			loadDependencies();
		}
	}, [isOpen, selectedProject, loadDependencies]);

	const filteredDependencies = dependencies.filter((dep) =>
		dep.name.toLowerCase().includes(searchQuery.toLowerCase()),
	);

	const filteredVulnerabilities = vulnerabilities.filter(
		(vuln) =>
			vuln.package.toLowerCase().includes(searchQuery.toLowerCase()) ||
			vuln.title.toLowerCase().includes(searchQuery.toLowerCase()),
	);

	const handleRefresh = () => {
		loadDependencies();
	};

	return (
		<Dialog open={isOpen} onOpenChange={closeDialog}>
			<DialogContent className="max-w-4xl max-h-[80vh]">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<Shield className="h-5 w-5" />
						{t("dialogs:dependencySentinel.title", "Dependency Sentinel")}
					</DialogTitle>
					<DialogDescription>
						{t(
							"dialogs:dependencySentinel.description",
							"Monitor dependencies for security vulnerabilities and outdated packages",
						)}
					</DialogDescription>
				</DialogHeader>

				<div className="flex flex-col gap-4 py-4">
					{/* Search and Refresh */}
					<div className="flex items-center gap-2">
						<div className="relative flex-1">
							<Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
							<Input
								placeholder={t(
									"dialogs:dependencySentinel.searchPlaceholder",
									"Search dependencies...",
								)}
								value={searchQuery}
								onChange={(e) => setSearchQuery(e.target.value)}
								className="pl-10 border-2 border-yellow-400 focus:border-yellow-500 focus-visible:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-200"
								style={{
									border: "2px solid rgb(250, 204, 21)",
									borderRadius: "0.5rem",
									outline: "none",
								}}
							/>
						</div>
						<Button
							variant="outline"
							size="icon"
							onClick={handleRefresh}
							disabled={isLoading}
						>
							<RefreshCw
								className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
							/>
						</Button>
					</div>

					{/* Tabs */}
					<Tabs
						value={activeTab}
						onValueChange={setActiveTab}
						className="flex-1"
					>
						<TabsList className="grid w-full grid-cols-2">
							<TabsTrigger
								value="dependencies"
								className="flex items-center gap-2"
							>
								<Package className="h-4 w-4" />
								{t("dialogs:dependencySentinel.dependencies", "Dependencies")}
								<Badge variant="secondary">{dependencies.length}</Badge>
							</TabsTrigger>
							<TabsTrigger
								value="vulnerabilities"
								className="flex items-center gap-2"
							>
								<AlertTriangle className="h-4 w-4" />
								{t(
									"dialogs:dependencySentinel.vulnerabilities",
									"Vulnerabilities",
								)}
								<Badge variant="destructive">{vulnerabilities.length}</Badge>
							</TabsTrigger>
						</TabsList>

						<TabsContent value="dependencies" className="mt-4">
							<ScrollArea className="h-[400px]">
								<div className="space-y-3">
									{(() => {
										if (isLoading) {
											return (
												<div className="flex items-center justify-center py-8">
													<Loader2 className="h-6 w-6 animate-spin" />
													<span className="ml-2">
														{t("common:loading", "Loading...")}
													</span>
												</div>
											);
										}

										if (filteredDependencies.length === 0) {
											const emptyMessage = searchQuery
												? t(
														"dialogs:dependencySentinel.noDependenciesFound",
														"No dependencies found matching your search",
													)
												: t(
														"dialogs:dependencySentinel.noDependencies",
														"No dependencies found",
													);

											return (
												<div className="text-center py-8 text-muted-foreground">
													{emptyMessage}
												</div>
											);
										}

										return filteredDependencies.map((dep) => (
											<Card key={dep.name}>
												<CardHeader className="pb-3">
													<div className="flex items-center justify-between">
														<CardTitle className="text-lg">
															{dep.name}
														</CardTitle>
														<div className="flex items-center gap-2">
															<Badge
																variant={
																	dep.type === "production"
																		? "default"
																		: "secondary"
																}
															>
																{dep.type}
															</Badge>
															<Badge className={STATUS_COLORS[dep.status]}>
																{dep.status}
															</Badge>
															{dep.severity && (
																<Badge
																	className={SEVERITY_COLORS[dep.severity]}
																>
																	{dep.severity}
																</Badge>
															)}
														</div>
													</div>
													<CardDescription>{dep.version}</CardDescription>
												</CardHeader>
												<CardContent>
													<p className="text-sm text-muted-foreground mb-2">
														{dep.description}
													</p>
													{dep.recommendation && (
														<div className="flex items-start gap-2 text-sm">
															<CheckCircle className="h-4 w-4 text-green-600 mt-0.5 shrink-0" />
															<span className="text-green-700">
																{dep.recommendation}
															</span>
														</div>
													)}
												</CardContent>
											</Card>
										));
									})()}
								</div>
							</ScrollArea>
						</TabsContent>

						<TabsContent value="vulnerabilities" className="mt-4">
							<ScrollArea className="h-[400px]">
								<div className="space-y-3">
									{(() => {
										if (isLoading) {
											return (
												<div className="flex items-center justify-center py-8">
													<Loader2 className="h-6 w-6 animate-spin" />
													<span className="ml-2">
														{t("common:loading", "Loading...")}
													</span>
												</div>
											);
										}

										if (filteredVulnerabilities.length === 0) {
											const emptyMessage = searchQuery
												? t(
														"dialogs:dependencySentinel.noVulnerabilitiesFound",
														"No vulnerabilities found matching your search",
													)
												: t(
														"dialogs:dependencySentinel.noVulnerabilities",
														"No vulnerabilities found",
													);

											return (
												<div className="text-center py-8 text-muted-foreground">
													{emptyMessage}
												</div>
											);
										}

										return filteredVulnerabilities.map((vuln) => (
											<Card key={vuln.id}>
												<CardHeader className="pb-3">
													<div className="flex items-center justify-between">
														<CardTitle className="text-lg">
															{vuln.title}
														</CardTitle>
														<div className="flex items-center gap-2">
															<Badge className={SEVERITY_COLORS[vuln.severity]}>
																{vuln.severity}
															</Badge>
															{vuln.cve && (
																<Badge variant="outline">{vuln.cve}</Badge>
															)}
														</div>
													</div>
													<CardDescription>
														{vuln.package}@{vuln.version}
													</CardDescription>
												</CardHeader>
												<CardContent>
													<p className="text-sm text-muted-foreground mb-2">
														{vuln.description}
													</p>
													<div className="flex items-start gap-2 text-sm">
														<AlertTriangle className="h-4 w-4 text-orange-600 mt-0.5 shrink-0" />
														<span className="text-orange-700">
															{vuln.recommendation}
														</span>
													</div>
												</CardContent>
											</Card>
										));
									})()}
								</div>
							</ScrollArea>
						</TabsContent>
					</Tabs>
				</div>

				<DialogFooter>
					<Button variant="outline" onClick={closeDialog}>
						{t("common:close", "Close")}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
