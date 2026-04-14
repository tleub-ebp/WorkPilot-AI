#!/usr/bin/env node

/**
 * BMAD Hybrid CLI
 * Combines autonomous execution with BMAD-METHOD structured workflows
 *
 * Usage:
 *   bmad install --modules autonomous,bmm,bmb --tools claude-code
 *   bmad-help
 *   bmad-quick-dev
 *   bmad-party-mode "task description"
 */

import {
	existsSync,
	mkdirSync,
	readdirSync,
	readFileSync,
	statSync,
	writeFileSync,
} from "node:fs";
import { join } from "node:path";

class BMADCLI {
	constructor() {
		this.configPath = join(process.cwd(), ".bmad", "config.yaml");
		this.memoryPath = join(process.cwd(), ".bmad", "memory");
		this.agentsPath = join(process.cwd(), "claude-skills", "agents");
		this.ensureDirectories();
	}

	ensureDirectories() {
		const dirs = [".bmad", ".bmad/memory", ".bmad/logs"];
		dirs.forEach((dir) => {
			const fullPath = join(process.cwd(), dir);
			if (!existsSync(fullPath)) {
				mkdirSync(fullPath, { recursive: true });
			}
		});
	}

	async install(options = {}) {
		console.log("🚀 Installing BMAD Hybrid System...");

		const modules = options.modules || "autonomous,bmm,bmb";
		const tools = options.tools || "claude-code";

		console.log(`📦 Modules: ${modules}`);
		console.log(`🛠️  Tools: ${tools}`);

		// Install Autonomous Core
		if (modules.includes("autonomous")) {
			await this.installAutonomousCore();
		}

		// Install BMAD Method (BMM)
		if (modules.includes("bmm")) {
			await this.installBMADMethod();
		}

		// Install BMAD Builder (BMB)
		if (modules.includes("bmb")) {
			await this.installBMADBuilder();
		}

		// Install tools
		if (tools.includes("claude-code")) {
			await this.installClaudeCode();
		}

		// Create configuration
		await this.createConfiguration(modules, tools);

		// Initialize memory system
		await this.initializeMemory();

		console.log("✅ BMAD Hybrid System installed successfully!");
		console.log('💡 Run "bmad-help" for usage instructions');
	}

	async installAutonomousCore() {
		console.log("🔧 Installing Autonomous Core...");

		// Create Autonomous configuration
		const autonomousConfig = {
			autonomous_execution: true,
			parallel_agents: 12,
			quality_scorer: true,
			adaptive_intelligence: true,
			memory_integration: true,
		};

		this.saveModuleConfig("autonomous", autonomousConfig);
		console.log("✅ Autonomous Core installed");
	}

	async installBMADMethod() {
		console.log("🔄 Installing BMAD Method...");

		// Create BMAD configuration
		const bmmConfig = {
			structured_workflows: true,
			agile_facilitation: true,
			scale_adaptive: true,
			party_mode: true,
			workflow_count: 34,
			specialized_agents: 12,
		};

		this.saveModuleConfig("bmm", bmmConfig);
		console.log("✅ BMAD Method installed");
	}

	async installBMADBuilder() {
		console.log("🏗️  Installing BMAD Builder...");

		// Create BMB configuration
		const bmbConfig = {
			persistent_memory: true,
			custom_agents: true,
			skill_compliant: true,
			composable_workflows: true,
			memory_bank: true,
		};

		this.saveModuleConfig("bmb", bmbConfig);
		console.log("✅ BMAD Builder installed");
	}

	async installClaudeCode() {
		console.log("🤖 Installing Claude Code integration...");

		// Claude Code is assumed to be available
		const claudeConfig = {
			integration_enabled: true,
			hybrid_agents: true,
			memory_sync: true,
			workflow_integration: true,
		};

		this.saveModuleConfig("claude-code", claudeConfig);
		console.log("✅ Claude Code integration configured");
	}

	async createConfiguration(_modules, _tools) {
		const config = {
			version: "1.0.0",
			created: new Date().toISOString(),
			modules: {},
			tools: {},
			hybrid_mode: {
				enabled: true,
				party_mode: true,
				memory_persistence: true,
				scale_adaptive: true,
			},
			agents: {
				hybrid_count: 15,
				autonomous_core: 12,
				bmm_specialized: 12,
				memory_enabled: true,
			},
		};

		// Save main configuration
		const yamlContent = this.generateYAML(config);
		writeFileSync(this.configPath, yamlContent, "utf8");

		console.log("📝 Configuration saved to", this.configPath);
	}

	generateYAML(obj, indent = 0) {
		const spaces = "  ".repeat(indent);
		let yaml = "";

		for (const [key, value] of Object.entries(obj)) {
			if (value === null || value === undefined) {
				yaml += `${spaces}${key}: null\n`;
			} else if (typeof value === "object" && !Array.isArray(value)) {
				yaml += `${spaces}${key}:\n`;
				yaml += this.generateYAML(value, indent + 1);
			} else if (Array.isArray(value)) {
				yaml += `${spaces}${key}:\n`;
				value.forEach((item) => {
					if (typeof item === "object") {
						yaml += `${spaces}  -\n`;
						yaml += this.generateYAML(item, indent + 2).replace(
							/^ {2}/,
							"    ",
						);
					} else {
						yaml += `${spaces}  - ${item}\n`;
					}
				});
			} else {
				yaml += `${spaces}${key}: ${value}\n`;
			}
		}

		return yaml;
	}

	getModuleConfig(module) {
		const configs = {
			autonomous: {
				autonomous_execution: true,
				parallel_agents: 12,
				quality_scorer: true,
				adaptive_intelligence: true,
			},
			bmm: {
				structured_workflows: true,
				agile_facilitation: true,
				scale_adaptive: true,
				party_mode: true,
			},
			bmb: {
				persistent_memory: true,
				custom_agents: true,
				skill_compliant: true,
				composable_workflows: true,
			},
		};
		return configs[module] || {};
	}

	getToolConfig(tool) {
		const configs = {
			"claude-code": {
				integration_enabled: true,
				hybrid_agents: true,
				memory_sync: true,
			},
		};
		return configs[tool] || {};
	}

	saveModuleConfig(module, config) {
		const modulePath = join(".bmad", `${module}.json`);
		writeFileSync(modulePath, JSON.stringify(config, null, 2));
	}

	async initializeMemory() {
		console.log("🧠 Initializing Memory System...");

		const memoryStructure = {
			project_memory: {
				architecture_decisions: [],
				performance_insights: [],
				business_requirements: [],
				workflow_history: [],
			},
			agent_memory: {
				hybrid_agents: {},
				ebp_agents: {},
				bmm_agents: {},
			},
			workflow_memory: {
				completed_workflows: [],
				optimization_patterns: [],
				decision_rationales: [],
			},
			quality_scores: {},
			performance_benchmarks: {},
		};

		const memoryPath = join(this.memoryPath, "structure.json");
		writeFileSync(memoryPath, JSON.stringify(memoryStructure, null, 2));

		console.log("✅ Memory System initialized");
	}

	async help() {
		console.log(`
🤖 BMAD Hybrid CLI - Help

USAGE:
  bmad install [options]     Install hybrid system
  bmad-help                  Show this help
  bmad-quick-dev             Quick development setup
  bmad-party-mode <task>     Activate party mode
  bmad-status                Show system status
  bmad-memory                Show memory statistics

INSTALL OPTIONS:
  --modules <list>    Modules to install (autonomous,bmm,bmb)
  --tools <list>      Tools to install (claude-code)

EXAMPLES:
  bmad install --modules autonomous,bmm,bmb --tools claude-code
  bmad-quick-dev
  bmad-party-mode "Design microservices architecture"
  bmad-status

HYBRID AGENTS:
  /bmad-net-architect            Hybrid .NET architect
  /bmad-dotnet-framework-48-expert .NET Framework 4.8 expert (legacy)
  /bmad-performance-analyst      Hybrid performance analyst
  /bmad-scrum-master             Agile project management

PARTY MODE:
  Mobilizes multiple hybrid agents for complex tasks
  Combines autonomous execution + BMAD structured workflows

MEMORY SYSTEM:
  Persistent memory across sessions
  Learning from architectural decisions
  Performance pattern recognition
  Workflow optimization history

CONFIGURATION:
  .bmad/config.yaml - Main configuration
  .bmad/memory/     - Memory storage
  claude-skills/agents/  - Hybrid agents definitions

For more information, see the documentation.
        `);
	}

	async quickDev() {
		console.log("⚡ Quick Development Setup...");

		await this.createConfiguration("autonomous,bmm", "claude-code");

		console.log("🚀 Quick development environment ready!");
		console.log(
			"💡 Use /bmad-net-architect or /bmad-performance-analyst to start",
		);
	}

	async partyMode(task) {
		console.log(`🎉 Party Mode Activated: "${task}"`);

		// Party mode configuration
		const partyConfig = {
			mode: "party",
			task: task,
			agents: [
				"bmad-net-architect",
				"bmad-dotnet-framework-48-expert",
				"bmad-performance-analyst",
				"bmad-scrum-master",
				"net-architect",
				"performance-analyst",
			],
			workflow: "collaborative-sprint",
			duration: "2-4 hours",
			collaboration: {
				real_time: true,
				memory_sharing: true,
				quality_scoring: true,
			},
		};

		// Save party mode session
		const sessionPath = join(".bmad", "party-session.json");
		writeFileSync(sessionPath, JSON.stringify(partyConfig, null, 2));

		console.log("👥 Party Mode Agents Mobilized:");
		partyConfig.agents.forEach((agent) => console.log(`   - ${agent}`));
		console.log(`⏱️  Estimated Duration: ${partyConfig.duration}`);
		console.log("🧠 Memory sharing enabled");
		console.log("📊 Quality scoring active");
		console.log("\n🎯 Party Mode session started!");
	}

	async status() {
		console.log("📊 BMAD System Status");

		try {
			// Check configuration
			if (existsSync(this.configPath)) {
				console.log("✅ Configuration loaded");
			} else {
				console.log("❌ Configuration not found - run install first");
				return;
			}

			// Check memory system
			if (existsSync(this.memoryPath)) {
				const memoryFiles = readdirSync(this.memoryPath);
				console.log(`✅ Memory system active (${memoryFiles.length} files)`);
			} else {
				console.log("❌ Memory system not initialized");
			}

			// Check agents
			if (existsSync(this.agentsPath)) {
				const agents = readdirSync(this.agentsPath);
				const hybridAgents = agents.filter((agent) =>
					agent.startsWith("bmad-"),
				);
				console.log(
					`✅ Agents available: ${agents.length} total, ${hybridAgents.length} hybrid`,
				);

				if (hybridAgents.length > 0) {
					console.log("   Hybrid agents:");
					hybridAgents.forEach((agent) =>
						console.log(`     - ${agent.replace(".md", "")}`),
					);
				}
			} else {
				console.log("❌ Agents directory not found");
			}

			console.log("\n🤖 System Ready for Hybrid Operations!");
		} catch (error) {
			console.error("❌ Error checking status:", error.message);
		}
	}

	async memory() {
		console.log("🧠 Memory System Statistics");

		try {
			if (!existsSync(this.memoryPath)) {
				console.log("❌ Memory system not initialized");
				return;
			}

			const memoryFiles = readdirSync(this.memoryPath);
			console.log(`📁 Memory files: ${memoryFiles.length}`);

			memoryFiles.forEach((file) => {
				const filePath = join(this.memoryPath, file);
				const stats = statSync(filePath);
				console.log(`   📄 ${file} (${stats.size} bytes)`);
			});

			// Load memory structure if available
			const structurePath = join(this.memoryPath, "structure.json");
			if (existsSync(structurePath)) {
				const structure = JSON.parse(readFileSync(structurePath, "utf8"));

				console.log("\n📊 Memory Contents:");
				Object.entries(structure).forEach(([key, value]) => {
					if (Array.isArray(value)) {
						console.log(`   ${key}: ${value.length} entries`);
					} else if (typeof value === "object") {
						const count = Object.keys(value).length;
						console.log(`   ${key}: ${count} items`);
					}
				});
			}
		} catch (error) {
			console.error("❌ Error reading memory:", error.message);
		}
	}
}

// CLI Command Handler
async function main() {
	const cli = new BMADCLI();
	const args = process.argv.slice(2);
	const command = args[0];

	switch (command) {
		case "install": {
			const options = {};
			for (let i = 1; i < args.length; i++) {
				if (args[i].startsWith("--modules=")) {
					options.modules = args[i].split("=")[1];
				} else if (args[i].startsWith("--tools=")) {
					options.tools = args[i].split("=")[1];
				}
			}
			await cli.install(options);
			break;
		}

		case "help":
			await cli.help();
			break;

		case "quick-dev":
			await cli.quickDev();
			break;

		case "party-mode": {
			const task = args[1];
			if (!task) {
				console.error("❌ Please provide a task description");
				process.exit(1);
			}
			await cli.partyMode(task);
			break;
		}

		case "status":
			await cli.status();
			break;

		case "memory":
			await cli.memory();
			break;

		default:
			console.error("❌ Unknown command:", command);
			console.log('💡 Run "bmad-help" for usage instructions');
			process.exit(1);
	}
}

// Export for testing
export default { BMADCLI };

// Run CLI if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
	try {
		await main();
	} catch (error) {
		console.error(error);
		process.exit(1);
	}
}
