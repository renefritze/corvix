interface UndoToastProps {
	readonly count: number;
	readonly onUndoAll: () => void;
}

export function UndoToast({ count, onUndoAll }: UndoToastProps) {
	if (count === 0) return null;
	return (
		<div class="undo-toast" role="status" aria-live="polite">
			<span>
				{count} notification{count > 1 ? "s" : ""} dismissing…
			</span>
			<button type="button" onClick={onUndoAll}>
				Undo
			</button>
		</div>
	);
}
