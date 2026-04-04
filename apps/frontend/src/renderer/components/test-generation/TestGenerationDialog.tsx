import {
	Check,
	Copy,
	FlaskConical,
	Loader2,
	Play,
	Search,
	Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
	type CoverageGap,
	type GeneratedTest,
	useTestGenerationStore,
} from "../../stores/test-generation-store";
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
import { Label } from "../ui/label";
import { ScrollArea } from "../ui/scroll-area";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "../ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Textarea } from "../ui/textarea";
import { SmartFilePicker } from "./SmartFilePicker";

const PRIORITY_COLORS = {
	high: "bg-red-100 text-red-800",
	medium: "bg-yellow-100 text-yellow-800",
	low: "bg-green-100 text-green-800",
};

/**
 * TestGenerationDialog — AI-powered test generation dialog.
 *
 * Shows a dialog where users can analyze coverage gaps and generate
 * comprehensive test suites for their code.
 *
 * Usage:
 *   const { openDialog, closeDialog, isOpen } = useTestGenerationStore();
 *   <TestGenerationDialog />
 */
interface TestGenerationDialogProps {
	/** Called when tests are generated and should be applied */
	readonly onApplyTests?: (
		testFileContent: string,
		testFilePath: string,
	) => void;
}

export function TestGenerationDialog({
	onApplyTests,
}: TestGenerationDialogProps) {
	const { t } = useTranslation(["testGeneration", "common"]);
	const [copied, setCopied] = useState(false);
	const [activeTab, setActiveTab] = useState("analyze");
	const [userStory, setUserStory] = useState("");
	const [targetModule, setTargetModule] = useState("");
	const [tddDescription, setTddDescription] = useState("");

	const {
		isOpen,
		closeDialog,
		phase,
		status,
		result,
		error,
		selectedFile,
		existingTestPath,
		coverageTarget,
		setCoverageTarget,
		tddLanguage,
		setTddLanguage,
		tddSnippetType,
		setTddSnippetType,
		reset,
		setSelectedFile,
		analyzeCoverage,
		generateUnitTests,
		generateE2ETests,
		generateTDDTests,
	} = useTestGenerationStore();

	// Reset state when dialog closes
	useEffect(() => {
		if (!isOpen) {
			reset();
			setActiveTab("analyze");
			setUserStory("");
			setTargetModule("");
			setTddDescription("");
			setCopied(false);
		}
	}, [isOpen, reset]);

	const handleAnalyzeCoverage = useCallback(async () => {
		if (!selectedFile) return;
		await analyzeCoverage(selectedFile, existingTestPath || undefined);
	}, [selectedFile, existingTestPath, analyzeCoverage]);

	const handleGenerateUnitTests = useCallback(async () => {
		if (!selectedFile) return;
		await generateUnitTests(
			selectedFile,
			existingTestPath || undefined,
			coverageTarget,
		);
	}, [selectedFile, existingTestPath, coverageTarget, generateUnitTests]);

	const handleGenerateE2ETests = useCallback(async () => {
		if (!userStory.trim() || !targetModule.trim()) return;
		await generateE2ETests(userStory, targetModule);
	}, [userStory, targetModule, generateE2ETests]);

	const handleGenerateTDDTests = useCallback(async () => {
		if (!tddDescription.trim()) return;
		await generateTDDTests({
			description: tddDescription,
			language: tddLanguage,
			snippet_type: tddSnippetType,
		});
	}, [tddDescription, tddLanguage, tddSnippetType, generateTDDTests]);

	const handleCopyToClipboard = useCallback((content: string) => {
		navigator.clipboard.writeText(content);
		setCopied(true);
		setTimeout(() => setCopied(false), 2000);
	}, []);

	const handleApplyTests = useCallback(() => {
		if (result && onApplyTests) {
			onApplyTests(result.test_file_content, result.test_file_path);
			closeDialog();
		}
	}, [result, onApplyTests, closeDialog]);

	const renderCoverageGaps = (gaps: CoverageGap[]) => (
		<div className="space-y-3">
			{gaps.map((gap) => (
				<Card key={`${gap.function.full_name}-${gap.function.line_number}`}>
					<CardContent className="pt-4">
						<div className="flex items-center justify-between mb-2">
							<h4 className="font-mono text-sm">{gap.function.full_name}</h4>
							<Badge className={PRIORITY_COLORS[gap.priority]}>
								{gap.priority} priority
							</Badge>
						</div>
						<p className="text-sm text-gray-600 mb-2">{gap.reason}</p>
						<div className="text-xs text-gray-500">
							Line: {gap.function.line_number} | Complexity:{" "}
							{gap.function.complexity} | Tests needed:{" "}
							{gap.suggested_test_count}
						</div>
					</CardContent>
				</Card>
			))}
		</div>
	);

	const renderGeneratedTests = (tests: GeneratedTest[]) => (
		<div className="space-y-4">
			{tests.map((test) => (
				<Card key={test.test_name}>
					<CardHeader>
						<div className="flex items-center justify-between">
							<CardTitle className="text-sm font-mono">
								{test.test_name}
							</CardTitle>
							<Badge variant="outline">{test.test_type}</Badge>
						</div>
						<CardDescription>{test.description}</CardDescription>
					</CardHeader>
					<CardContent>
						<ScrollArea className="h-32 w-full">
							<pre className="text-xs bg-gray-50 p-2 rounded">
								{test.test_code}
							</pre>
						</ScrollArea>
					</CardContent>
				</Card>
			))}
		</div>
	);

	return (
		<Dialog open={isOpen} onOpenChange={closeDialog}>
			<DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
				<DialogHeader>
					<DialogTitle className="flex items-center gap-2">
						<FlaskConical className="w-5 h-5" />
						{t("testGeneration:title", {
							defaultValue: "Test Generation Agent",
						})}
					</DialogTitle>
					<DialogDescription>
						{t("testGeneration:description", {
							defaultValue:
								"Analyze coverage gaps and generate comprehensive test suites for your code.",
						})}
					</DialogDescription>
				</DialogHeader>

				<Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
					<TabsList className="grid w-full grid-cols-4">
						<TabsTrigger value="analyze">
							{t("testGeneration:tabs.analyze", { defaultValue: "Analyze" })}
						</TabsTrigger>
						<TabsTrigger value="unit">
							{t("testGeneration:tabs.unit", { defaultValue: "Unit Tests" })}
						</TabsTrigger>
						<TabsTrigger value="e2e">
							{t("testGeneration:tabs.e2e", { defaultValue: "E2E Tests" })}
						</TabsTrigger>
						<TabsTrigger value="tdd">
							{t("testGeneration:tabs.tdd", { defaultValue: "TDD Mode" })}
						</TabsTrigger>
					</TabsList>

					<TabsContent value="analyze" className="space-y-4">
						<div className="space-y-4">
							<div>
								<Label>
									{t("testGeneration:sourceFile.label", {
										defaultValue: "Source File",
									})}
								</Label>
								<SmartFilePicker
									value={selectedFile}
									onChange={setSelectedFile}
									tabType="analyze"
									placeholder={t("testGeneration:filePicker.selectFile")}
								/>
							</div>

							{existingTestPath && (
								<div>
									<Label htmlFor="existing-test">
										{t("testGeneration:existingTest.label", {
											defaultValue: "Existing Test File",
										})}
									</Label>
									<Input id="existing-test" value={existingTestPath} readOnly />
								</div>
							)}

							<div className="flex gap-2">
								<Button
									onClick={handleAnalyzeCoverage}
									disabled={phase === "analyzing" || !selectedFile}
								>
									{phase === "analyzing" ? (
										<Loader2 className="w-4 h-4 mr-2 animate-spin" />
									) : (
										<Search className="w-4 h-4 mr-2" />
									)}
									{t("testGeneration:analyzeCoverage", {
										defaultValue: "Analyze Coverage",
									})}
								</Button>
								<Button
									onClick={handleGenerateUnitTests}
									disabled={phase === "generating" || !selectedFile}
									variant="outline"
								>
									{phase === "generating" ? (
										<Loader2 className="w-4 h-4 mr-2 animate-spin" />
									) : (
										<Zap className="w-4 h-4 mr-2" />
									)}
									{t("testGeneration:generateTests", {
										defaultValue: "Generate Tests",
									})}
								</Button>
							</div>

							{status && (
								<div className="text-sm text-gray-600">
									{phase === "analyzing" && (
										<Loader2 className="w-3 h-3 inline mr-2 animate-spin" />
									)}
									{phase === "generating" && (
										<Loader2 className="w-3 h-3 inline mr-2 animate-spin" />
									)}
									{status}
								</div>
							)}

							{error && (
								<div className="text-sm text-red-600 bg-red-50 p-2 rounded">
									{error}
								</div>
							)}

							{result && result.coverage_gaps.length > 0 && (
								<div>
									<h3 className="text-lg font-semibold mb-3">
										{t("testGeneration:result.coverageGapsFound", {
											defaultValue: "Coverage Gaps Found",
										})}
									</h3>
									{renderCoverageGaps(result.coverage_gaps)}
								</div>
							)}

							{result && result.generated_tests.length > 0 && (
								<div>
									<h3 className="text-lg font-semibold mb-3">
										{t("testGeneration:result.generatedTests", {
											defaultValue: "Generated Tests",
										})}
									</h3>
									{renderGeneratedTests(result.generated_tests)}
								</div>
							)}
						</div>
					</TabsContent>

					<TabsContent value="unit" className="space-y-4">
						<div className="space-y-4">
							<div>
								<Label>
									{t("testGeneration:sourceFile.label", {
										defaultValue: "Source File",
									})}
								</Label>
								<SmartFilePicker
									value={selectedFile}
									onChange={setSelectedFile}
									tabType="unit"
									placeholder={t("testGeneration:filePicker.selectFile")}
								/>
							</div>

							<div>
								<Label htmlFor="coverage-target">
									{t("testGeneration:coverageTarget.label", {
										defaultValue: "Coverage Target (%)",
									})}
									<span className="ml-2 font-semibold">{coverageTarget}%</span>
								</Label>
								<Input
									id="coverage-target"
									type="range"
									min="10"
									max="100"
									step="5"
									value={coverageTarget}
									onChange={(e) =>
										setCoverageTarget(Number.parseInt(e.target.value, 10))
									}
									className="mt-1"
								/>
							</div>

							<Button
								onClick={handleGenerateUnitTests}
								disabled={phase === "generating" || !selectedFile}
								className="w-full"
							>
								{phase === "generating" ? (
									<Loader2 className="w-4 h-4 mr-2 animate-spin" />
								) : (
									<Play className="w-4 h-4 mr-2" />
								)}
								Generate Unit Tests
							</Button>

							{result && result.generated_tests.length > 0 && (
								<div>
									<div className="flex items-center justify-between mb-3">
										<h3 className="text-lg font-semibold">
											{t("testGeneration:result.generatedUnitTests", {
												defaultValue: "Generated Unit Tests",
											})}
										</h3>
										<div className="flex gap-2">
											<Button
												size="sm"
												variant="outline"
												onClick={() =>
													handleCopyToClipboard(result.test_file_content)
												}
											>
												{copied ? (
													<Check className="w-3 h-3" />
												) : (
													<Copy className="w-3 h-3" />
												)}
												{t("testGeneration:actions.copyAll", {
													defaultValue: "Copy All",
												})}
											</Button>
											{onApplyTests && (
												<Button size="sm" onClick={handleApplyTests}>
													{t("testGeneration:actions.applyTests", {
														defaultValue: "Apply Tests",
													})}
												</Button>
											)}
										</div>
									</div>
									{renderGeneratedTests(result.generated_tests)}
								</div>
							)}
						</div>
					</TabsContent>

					<TabsContent value="e2e" className="space-y-4">
						<div className="space-y-4">
							<div>
								<Label htmlFor="user-story">
									{t("testGeneration:userStory.label", {
										defaultValue: "User Story",
									})}
								</Label>
								<Textarea
									id="user-story"
									value={userStory}
									onChange={(e) => setUserStory(e.target.value)}
									placeholder={t("testGeneration:userStory.placeholder", {
										defaultValue: "Describe the user story or scenario...",
									})}
									rows={4}
									className="border-2 border-yellow-400 focus:border-yellow-500 focus-visible:border-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-200"
									style={{
										border: "2px solid rgb(250, 204, 21)",
										borderRadius: "0.5rem",
										outline: "none",
									}}
								/>
							</div>

							<div>
								<Label htmlFor="target-module">
									{t("testGeneration:targetModule.label", {
										defaultValue: "Target Module",
									})}
								</Label>
								<Input
									id="target-module"
									value={targetModule}
									onChange={(e) => setTargetModule(e.target.value)}
									placeholder={t("testGeneration:targetModule.placeholder", {
										defaultValue: "e.g., src/auth/login.py",
									})}
								/>
							</div>

							<Button
								onClick={handleGenerateE2ETests}
								disabled={
									phase === "generating" ||
									!userStory.trim() ||
									!targetModule.trim()
								}
								className="w-full"
							>
								{phase === "generating" ? (
									<Loader2 className="w-4 h-4 mr-2 animate-spin" />
								) : (
									<Play className="w-4 h-4 mr-2" />
								)}
								Generate E2E Tests
							</Button>

							{result && result.generated_tests.length > 0 && (
								<div>
									<div className="flex items-center justify-between mb-3">
										<h3 className="text-lg font-semibold">
											{t("testGeneration:result.generatedE2ETests", {
												defaultValue: "Generated E2E Tests",
											})}
										</h3>
										<div className="flex gap-2">
											<Button
												size="sm"
												variant="outline"
												onClick={() =>
													handleCopyToClipboard(result.test_file_content)
												}
											>
												{copied ? (
													<Check className="w-3 h-3" />
												) : (
													<Copy className="w-3 h-3" />
												)}
												{t("testGeneration:actions.copyAll", {
													defaultValue: "Copy All",
												})}
											</Button>
											{onApplyTests && (
												<Button size="sm" onClick={handleApplyTests}>
													{t("testGeneration:actions.applyTests", {
														defaultValue: "Apply Tests",
													})}
												</Button>
											)}
										</div>
									</div>
									{renderGeneratedTests(result.generated_tests)}
								</div>
							)}
						</div>
					</TabsContent>

					<TabsContent value="tdd" className="space-y-4">
						<div className="space-y-4">
							<div>
								<Label>
									{t("testGeneration:snippetType.label", {
										defaultValue: "Snippet Type",
									})}
								</Label>
								<Select
									value={tddSnippetType}
									onValueChange={setTddSnippetType}
								>
									<SelectTrigger>
										<SelectValue />
									</SelectTrigger>
									<SelectContent className="z-200">
										<SelectItem value="function">
											{t("testGeneration:snippetType.options.function", {
												defaultValue: "Function",
											})}
										</SelectItem>
										<SelectItem value="class">
											{t("testGeneration:snippetType.options.class", {
												defaultValue: "Class",
											})}
										</SelectItem>
										<SelectItem value="component">
											{t("testGeneration:snippetType.options.component", {
												defaultValue: "Component",
											})}
										</SelectItem>
										<SelectItem value="api">
											{t("testGeneration:snippetType.options.api", {
												defaultValue: "API Endpoint",
											})}
										</SelectItem>
									</SelectContent>
								</Select>
							</div>

							<div>
								<Label>
									{t("testGeneration:language.label", {
										defaultValue: "Language",
									})}
								</Label>
								<Select value={tddLanguage} onValueChange={setTddLanguage}>
									<SelectTrigger>
										<SelectValue />
									</SelectTrigger>
									<SelectContent className="z-200">
										<SelectItem value="typescript">TypeScript</SelectItem>
										<SelectItem value="javascript">JavaScript</SelectItem>
										<SelectItem value="python">Python</SelectItem>
										<SelectItem value="java">Java</SelectItem>
										<SelectItem value="csharp">C#</SelectItem>
									</SelectContent>
								</Select>
							</div>

							<div>
								<Label htmlFor="tdd-description">
									{t("testGeneration:tdd.description.label", {
										defaultValue: "What should this code do?",
									})}
								</Label>
								<Textarea
									id="tdd-description"
									value={tddDescription}
									onChange={(e) => setTddDescription(e.target.value)}
									placeholder={t("testGeneration:tdd.description.placeholder", {
										defaultValue:
											"Describe the behaviour to implement. Example: a function that calculates the total price of a cart including taxes and discounts, handling empty carts and negative quantities.",
									})}
									rows={5}
								/>
							</div>

							<div className="flex gap-2">
								<Button
									onClick={handleGenerateTDDTests}
									disabled={phase === "generating" || !tddDescription.trim()}
									className="flex-1"
								>
									{phase === "generating" ? (
										<Loader2 className="w-4 h-4 mr-2 animate-spin" />
									) : (
										<Play className="w-4 h-4 mr-2" />
									)}
									{t("testGeneration:actions.generate", {
										defaultValue: "Generate",
									})}
								</Button>
								<Button variant="outline" onClick={closeDialog}>
									{t("common:buttons:close", { defaultValue: "Close" })}
								</Button>
							</div>

							{result && result.generated_tests.length > 0 && (
								<div>
									<div className="flex items-center justify-between mb-3">
										<h3 className="text-lg font-semibold">
											{t("testGeneration:result.generatedTDDTests", {
												defaultValue: "Generated TDD Tests",
											})}
										</h3>
										<div className="flex gap-2">
											<Button
												size="sm"
												variant="outline"
												onClick={() =>
													handleCopyToClipboard(result.test_file_content)
												}
											>
												{copied ? (
													<Check className="w-3 h-3" />
												) : (
													<Copy className="w-3 h-3" />
												)}
												{t("testGeneration:actions.copyAll", {
													defaultValue: "Copy All",
												})}
											</Button>
											{onApplyTests && (
												<Button size="sm" onClick={handleApplyTests}>
													{t("testGeneration:actions.applyTests", {
														defaultValue: "Apply Tests",
													})}
												</Button>
											)}
										</div>
									</div>
									{renderGeneratedTests(result.generated_tests)}
								</div>
							)}
						</div>
					</TabsContent>
				</Tabs>

				<DialogFooter>
					<Button variant="outline" onClick={closeDialog}>
						{t("common:buttons:close", { defaultValue: "Close" })}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
