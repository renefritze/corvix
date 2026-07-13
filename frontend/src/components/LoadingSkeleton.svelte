<script lang="ts">
	const SKELETON_ROWS = Array.from({ length: 9 }, (_, i) => `skeleton-${i + 1}`);
</script>

<table class="nt-table" aria-label="Loading notifications">
	<thead>
		<tr>
			<th style="width: 28px"></th>
			<th>Title</th>
			<th>Repository</th>
			<th class="hide-mobile">Type</th>
			<th class="hide-mobile">Reason</th>
			<th>Score</th>
			<th>Updated</th>
			<th style="width: 36px"></th>
		</tr>
	</thead>
	<tbody>
		{#each SKELETON_ROWS as rowKey (rowKey)}
			<tr class="nt-skeleton-row">
				<td><span class="nt-skeleton dot"></span></td>
				<td><span class="nt-skeleton title"></span></td>
				<td><span class="nt-skeleton repo"></span></td>
				<td class="hide-mobile"><span class="nt-skeleton short"></span></td>
				<td class="hide-mobile"><span class="nt-skeleton short"></span></td>
				<td><span class="nt-skeleton score"></span></td>
				<td><span class="nt-skeleton time"></span></td>
				<td></td>
			</tr>
		{/each}
	</tbody>
</table>
