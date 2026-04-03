import { CommonModule } from "@angular/common";
import { Component, OnDestroy, OnInit } from "@angular/core";
import { Router } from "@angular/router";

@Component({
	selector: "app-{{componentName}}",
	standalone: true,
	imports: [CommonModule],
	templateUrl: "./{{componentName}}.component.html",
	styleUrls: ["./{{componentName}}.component.css"],
})
export class {
	{
	ComponentName;
}
}Component implements OnInit, OnDestroy
{
	constructor(private router: Router)

	ngOnInit();
	: void
	// Initialize component
	this.loadData();

	ngOnDestroy();
	: void
	{
		// Cleanup resources
	}

	private
	loadData();
	: void
	{
		// Load data for the component
	}

	public
	navigateToDetail(id: string)
	: void
	this.router.navigate(["/detail", id]);
}
