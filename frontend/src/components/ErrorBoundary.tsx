import { Component } from "preact";
import type { ComponentChildren } from "preact";

interface ErrorBoundaryProps {
	readonly children: ComponentChildren;
	readonly onRetry?: () => void;
}

interface ErrorBoundaryState {
	readonly hasError: boolean;
	readonly error: unknown;
}

export class ErrorBoundary extends Component<
	ErrorBoundaryProps,
	ErrorBoundaryState
> {
	state: ErrorBoundaryState = { hasError: false, error: null };

	componentDidCatch(error: unknown): void {
		this.setState({ hasError: true, error });
	}

	private reset = () => {
		this.setState({ hasError: false, error: null });
		this.props.onRetry?.();
	};

	render() {
		if (this.state.hasError) {
			const errorMessage =
				this.state.error instanceof Error
					? this.state.error.message
					: String(this.state.error ?? "Unknown error");
			return (
				<div class="empty-state error-state">
					<p class="empty-title">Something went wrong</p>
					<p class="empty-body">{errorMessage}</p>
					<button type="button" onClick={this.reset}>
						Try again
					</button>
				</div>
			);
		}
		return this.props.children;
	}
}
