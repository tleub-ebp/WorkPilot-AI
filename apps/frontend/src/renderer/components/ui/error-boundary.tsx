import { AlertTriangle, RefreshCw } from "lucide-react";
import React from "react";
import { useTranslation } from "react-i18next";
import { captureException } from "../../lib/sentry";
import { Button } from "./button";
import { Card, CardContent } from "./card";

interface ErrorBoundaryProps {
	readonly children: React.ReactNode;
	readonly fallback?: React.ReactNode;
	readonly onReset?: () => void;
}

interface ErrorBoundaryState {
	hasError: boolean;
	error: Error | null;
}

/**
 * Functional fallback UI that can access i18n hooks.
 */
function ErrorFallbackUI({
	error,
	onReset,
}: {
	readonly error: Error | null;
	readonly onReset: () => void;
}) {
	const { t } = useTranslation("errors");

	return (
		<Card className="border-destructive m-4" role="alert" aria-live="assertive">
			<CardContent className="pt-6">
				<div className="flex flex-col items-center gap-4 text-center">
					<AlertTriangle
						className="h-10 w-10 text-destructive"
						aria-hidden="true"
					/>
					<div className="space-y-2">
						<h3 className="font-semibold text-lg">{t("boundary.title")}</h3>
						<p className="text-sm text-muted-foreground">
							{t("boundary.description")}
						</p>
						{error && (
							<p
								className="text-xs text-muted-foreground font-mono bg-muted p-2 rounded max-w-md overflow-auto"
								role="log"
							>
								{error.message}
							</p>
						)}
					</div>
					<Button
						onClick={onReset}
						variant="outline"
						size="sm"
						aria-label={t("boundary.tryAgain")}
					>
						<RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
						{t("boundary.tryAgain")}
					</Button>
				</div>
			</CardContent>
		</Card>
	);
}

/**
 * Error boundary component to gracefully handle render errors.
 * Prevents the entire page from crashing when a component fails.
 */
export class ErrorBoundary extends React.Component<
	ErrorBoundaryProps,
	ErrorBoundaryState
> {
	constructor(props: ErrorBoundaryProps) {
		super(props);
		this.state = { hasError: false, error: null };
	}

	static getDerivedStateFromError(error: Error): ErrorBoundaryState {
		return { hasError: true, error };
	}

	componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
		console.error("ErrorBoundary caught an error:", error, errorInfo);

		// Report to Sentry with React component stack
		captureException(error, {
			componentStack: errorInfo.componentStack,
		});
	}

	handleReset = (): void => {
		this.setState({ hasError: false, error: null });
		this.props.onReset?.();
	};

	render(): React.ReactNode {
		if (this.state.hasError) {
			if (this.props.fallback) {
				return this.props.fallback;
			}

			return (
				<ErrorFallbackUI error={this.state.error} onReset={this.handleReset} />
			);
		}

		return this.props.children;
	}
}
