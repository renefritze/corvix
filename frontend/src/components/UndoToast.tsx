import styles from "./UndoToast.module.css";

interface UndoToastProps {
	readonly count: number;
	readonly onUndoAll: () => void;
}

export function UndoToast({ count, onUndoAll }: UndoToastProps) {
	if (count === 0) return null;
	return (
		<div class={styles.undoToast} role="status" aria-live="polite">
			<span>
				{count} notification{count > 1 ? "s" : ""} dismissing…
			</span>
			<button type="button" onClick={onUndoAll}>
				Undo
			</button>
		</div>
	);
}
