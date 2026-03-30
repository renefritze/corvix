interface EmptyStateProps {
  hasFilters: boolean;
  totalItems: number;
  onClearFilters: () => void;
  onRetry: () => void;
  error?: string | null;
}

export function EmptyState({ hasFilters, totalItems, onClearFilters, onRetry, error }: EmptyStateProps) {
  if (error) {
    return (
      <div class="empty-state error-state">
        <p class="empty-title">Failed to load</p>
        <p class="empty-body">{error}</p>
        <button type="button" onClick={onRetry}>Retry</button>
      </div>
    );
  }
  if (totalItems === 0) {
    return (
      <div class="empty-state">
        <p class="empty-title">All clear</p>
        <p class="empty-body">No notifications in this dashboard.</p>
      </div>
    );
  }
  return (
    <div class="empty-state">
      <p class="empty-title">No results</p>
      <p class="empty-body">No notifications match the current filters.</p>
      {hasFilters && (
        <button type="button" onClick={onClearFilters}>Clear filters</button>
      )}
    </div>
  );
}
