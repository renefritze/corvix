import { Component } from "preact";
import type { ComponentChildren } from "preact";

interface ErrorBoundaryProps {
	readonly children: ComponentChildren;
	readonly onRetry?: () => void;
}

interface ErrorBoundaryState {
	readonly error: Error | null;
}

export class ErrorBoundary extends Component<
	ErrorBoundaryProps,
	ErrorBoundaryState
> {
	state: ErrorBoundaryState = { error: null };

	componentDidCatch(error: Error): void {
		this.setState({ error });
	}

	private reset = () => {
		this.setState({ error: null });
		this.props.onRetry?.();
	};

	render() {
		if (this.state.error) {
			return (
				<div class="empty-state error-state">
					<p class="empty-title">Something went wrong</p>
					<p class="empty-body">{this.state.error.message}</p>
					<button type="button" onClick={this.reset}>
						Try again
					</button>
				</div>
			);
		}
		return this.props.children;
	}
}
