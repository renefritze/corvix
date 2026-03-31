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
		<table class="notification-table" aria-label="Loading notifications">
			<thead>
				<tr>
					<th style={{ width: "28px" }} />
					<th>Title</th>
					<th>Repository</th>
					<th class="hide-mobile">Type</th>
					<th class="hide-mobile">Reason</th>
					<th>Score</th>
					<th>Updated</th>
					<th style={{ width: "36px" }} />
				</tr>
			</thead>
			<tbody>
				{SKELETON_ROWS.map((rowKey) => (
					<tr key={rowKey} class="skeleton-row">
						<td>
							<span class="skeleton dot-skeleton" />
						</td>
						<td>
							<span class="skeleton title-skeleton" />
						</td>
						<td>
							<span class="skeleton repo-skeleton" />
						</td>
						<td class="hide-mobile">
							<span class="skeleton short-skeleton" />
						</td>
						<td class="hide-mobile">
							<span class="skeleton short-skeleton" />
						</td>
						<td>
							<span class="skeleton score-skeleton" />
						</td>
						<td>
							<span class="skeleton time-skeleton" />
						</td>
						<td />
					</tr>
				))}
			</tbody>
		</table>
	);
}
