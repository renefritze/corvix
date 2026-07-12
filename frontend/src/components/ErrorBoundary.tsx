import { Component } from "preact";
import type { ComponentChildren, ErrorInfo } from "preact";

interface ErrorBoundaryProps {
	readonly children: ComponentChildren;
	readonly onRetry?: () => void;
}

interface ErrorBoundaryState {
	readonly hasError: boolean;
	readonly error: unknown;
}

function formatError(error: unknown): string {
	if (error instanceof Error) return error.message;
	if (typeof error === "string") return error;
	if (error === null || error === undefined) return "Unknown error";
	try {
		return JSON.stringify(error);
	} catch {
		return "Unserializable error";
	}
}

export class ErrorBoundary extends Component<
	ErrorBoundaryProps,
	ErrorBoundaryState
> {
	state: ErrorBoundaryState = { hasError: false, error: null };

	componentDidCatch(error: unknown, _errorInfo: ErrorInfo): void {
		this.setState({ hasError: true, error });
	}

	private reset(): void {
		this.setState({ hasError: false, error: null });
		this.props.onRetry?.();
	}

	render() {
		if (this.state.hasError) {
			const errorMessage = formatError(this.state.error);
			return (
				<div class="empty-state error-state">
					<p class="empty-title">Something went wrong</p>
					<p class="empty-body">{errorMessage}</p>
					<button type="button" onClick={() => this.reset()}>
						Try again
					</button>
				</div>
			);
		}
		return this.props.children;
	}
}
