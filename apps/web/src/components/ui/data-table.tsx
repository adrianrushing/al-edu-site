import {
	type ColumnDef,
	type ColumnSizingState,
	flexRender,
	getCoreRowModel,
	useReactTable,
} from '@tanstack/react-table';
import { useState } from 'react';

import { Button } from '@/components/ui/button';

import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from '@/components/ui/table';

type DataTableProps<TData, TValue> = {
	columns: ColumnDef<TData, TValue>[];
	data: TData[];
	emptyMessage?: string;
	pagination?: {
		canPreviousPage: boolean;
		canNextPage: boolean;
		onPreviousPage: () => void;
		onNextPage: () => void;
		summary: string;
	};
};

export function DataTable<TData, TValue>({
	columns,
	data,
	emptyMessage = 'No rows match your filters.',
	pagination,
}: DataTableProps<TData, TValue>) {
	const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});

	const table = useReactTable({
		data,
		columns,
		enableColumnResizing: true,
		columnResizeMode: 'onChange',
		onColumnSizingChange: setColumnSizing,
		getCoreRowModel: getCoreRowModel(),
		state: {
			columnSizing,
		},
	});

	return (
		<div className="space-y-3">
			<div className="max-h-[68vh] w-full overflow-auto rounded-md border">
				<Table className="min-w-max">
					<TableHeader>
						{table.getHeaderGroups().map((headerGroup) => (
							<TableRow key={headerGroup.id}>
								{headerGroup.headers.map((header) => (
									<TableHead
										className="sticky top-0 z-10 whitespace-nowrap bg-card"
										key={header.id}
										style={{ width: header.getSize() }}
									>
										<div className="relative flex items-center gap-2 pr-2">
											{header.isPlaceholder
												? null
												: flexRender(
														header.column.columnDef
															.header,
														header.getContext(),
													)}
											{header.column.getCanResize() && (
												<div
													className="absolute right-0 top-0 h-full w-1 cursor-col-resize select-none bg-border/70 hover:bg-primary"
													onDoubleClick={() =>
														header.column.resetSize()
													}
													onMouseDown={header.getResizeHandler()}
													onTouchStart={header.getResizeHandler()}
												/>
											)}
										</div>
									</TableHead>
								))}
							</TableRow>
						))}
					</TableHeader>
					<TableBody>
						{table.getRowModel().rows.length > 0 ? (
							table.getRowModel().rows.map((row) => (
								<TableRow key={row.id}>
									{row.getVisibleCells().map((cell) => (
										<TableCell
											className="whitespace-nowrap"
											key={cell.id}
											style={{
												width: cell.column.getSize(),
											}}
										>
											{flexRender(
												cell.column.columnDef.cell,
												cell.getContext(),
											)}
										</TableCell>
									))}
								</TableRow>
							))
						) : (
							<TableRow>
								<TableCell
									className="h-24 text-center"
									colSpan={columns.length || 1}
								>
									{emptyMessage}
								</TableCell>
							</TableRow>
						)}
					</TableBody>
				</Table>
			</div>
			{pagination && (
				<div className="flex flex-wrap items-center justify-between gap-2">
					<p className="text-sm text-muted-foreground">
						{pagination.summary}
					</p>
					<div className="flex gap-2">
						<Button
							disabled={!pagination.canPreviousPage}
							onClick={pagination.onPreviousPage}
							size="sm"
							variant="outline"
						>
							Previous
						</Button>
						<Button
							disabled={!pagination.canNextPage}
							onClick={pagination.onNextPage}
							size="sm"
							variant="outline"
						>
							Next
						</Button>
					</div>
				</div>
			)}
		</div>
	);
}
