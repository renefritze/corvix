export function LoadingSkeleton() {
	return (
		<table class="notification-table" aria-label="Loading notifications">
			<thead>
				<tr>
					<th style={{ width: "28px" }}></th>
					<th>Title</th>
					<th>Repository</th>
					<th class="hide-mobile">Type</th>
					<th class="hide-mobile">Reason</th>
					<th>Score</th>
					<th>Updated</th>
					<th style={{ width: "36px" }}></th>
				</tr>
			</thead>
			<tbody>
				{Array.from({ length: 9 }, (_, i) => (
					<tr key={i} class="skeleton-row">
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
						<td></td>
					</tr>
				))}
			</tbody>
		</table>
	);
}
