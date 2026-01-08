const baseUrlLocal = "http://localhost:8888/";

export class DataService {
	constructor(baseUrl) {
		this.baseUrl = !baseUrl ? baseUrlLocal : baseUrl;
	}
	
	async getLatestSimulator({git_repo_url, git_branch}) {
		const url = new URL(`${this.baseUrl}/core/simulator/latest`);
			url.searchParams.set("git_repo_url", git_repo_url);
			url.searchParams.set("git_branch", git_branch);
		
			const res = await fetch(url.toString(), {
				method: "GET",
				headers: {
					accept: "application/json",
				},
			});
	
			if (!res.ok) {
				throw new Error(`GET latest simulator failed: ${res.status}`);
			}
			return res.json(); // EXACT response body
	}
	
	async uploadSimulatorVersion({
		git_commit_hash,
		git_repo_url,
		git_branch,
	}) {
		const res = await fetch(`${this.baseUrl}/core/simulator/upload`, {
			method: "POST",
			headers: {
				accept: "application/json",
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				git_commit_hash,
				git_repo_url,
				git_branch,
			}),
		});
	
		if (!res.ok) {
			throw new Error(`Upload simulator failed: ${res.status}`);
		}
	
		return res.json(); // EXACT response body
	}
	
	async runParcaSimulation({
		simulator_version,
		parca_config = {},
	}) {
		const res = await fetch(`${this.baseUrl}/core/simulation/parca`, {
			method: "POST",
			headers: {
				accept: "application/json",
				"Content-Type": "application/json",
			},
			body: JSON.stringify({
				simulator_version,
				parca_config,
			}),
		});
	
		if (!res.ok) {
			throw new Error(`PARCA simulation failed: ${res.status}`);
		}
	
		return res.json(); // EXACT response body
	}
	
	async executeWorkflow(gitRepoUrl="https://github.com/vivarium-collective/vEcoli", gitBranch="messages") {
		const latest = await this.getLatestSimulator({
			git_repo_url: gitRepoUrl,
			git_branch: gitBranch,
		});
		
		const uploaded = await this.uploadSimulatorVersion({
			git_commit_hash: latest.git_commit_hash,
			git_repo_url: latest.git_repo_url,
			git_branch: latest.git_branch,
		});
		
		const parcaResult = await this.runParcaSimulation({
			simulator_version: uploaded,
			parca_config: {},
		});
		
		console.log(parcaResult);

	}
}
