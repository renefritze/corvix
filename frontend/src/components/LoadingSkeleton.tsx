import styles from "./table.module.css";

const SKELETON_ROWS = [
	"skeleton-1",
	"skeleton-2",
	"skeleton-3",
	"skeleton-4",
	"skeleton-5",
	"skeleton-6",
	"skeleton-7",
	"skeleton-8",
	"skeleton-9",
];

export function LoadingSkeleton() {
	return (
		<table class={styles.notificationTable} aria-label="Loading notifications">
			<thead>
				<tr>
					<th style={{ width: "28px" }} />
					<th>Title</th>
					<th>Repository</th>
					<th class={styles.hideMobile}>Type</th>
					<th class={styles.hideMobile}>Reason</th>
					<th>Score</th>
					<th>Updated</th>
					<th style={{ width: "36px" }} />
				</tr>
			</thead>
			<tbody>
				{SKELETON_ROWS.map((rowKey) => (
					<tr key={rowKey} class={styles.skeletonRow}>
						<td>
							<span class={[styles.skeleton, styles.dotSkeleton].join(" ")} />
						</td>
						<td>
							<span class={[styles.skeleton, styles.titleSkeleton].join(" ")} />
						</td>
						<td>
							<span class={[styles.skeleton, styles.repoSkeleton].join(" ")} />
						</td>
						<td class={styles.hideMobile}>
							<span class={[styles.skeleton, styles.shortSkeleton].join(" ")} />
						</td>
						<td class={styles.hideMobile}>
							<span class={[styles.skeleton, styles.shortSkeleton].join(" ")} />
						</td>
						<td>
							<span class={[styles.skeleton, styles.scoreSkeleton].join(" ")} />
						</td>
						<td>
							<span class={[styles.skeleton, styles.timeSkeleton].join(" ")} />
						</td>
						<td />
					</tr>
				))}
			</tbody>
		</table>
	);
}
