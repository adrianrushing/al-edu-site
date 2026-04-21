import { type ReactNode, useId } from 'react';

import { Input } from '@/components/ui/input';

export function Field({
	children,
	label,
}: {
	children: ReactNode;
	label: string;
}) {
	return (
		<div className="grid gap-1 text-sm">
			<span className="font-medium text-muted-foreground">{label}</span>
			{children}
		</div>
	);
}

export function Metric({ label, value }: { label: string; value: string }) {
	return (
		<div className="rounded-md border bg-muted/30 p-3">
			<p className="text-xs text-muted-foreground">{label}</p>
			<p className="text-lg font-semibold">{value}</p>
		</div>
	);
}

export function RangeField({
	disabled,
	label,
	max,
	min,
	onChange,
	onCommit,
	step,
	suffix,
	value,
}: {
	disabled?: boolean;
	label: string;
	max: number;
	min: number;
	onChange: (value: number) => void;
	onCommit?: () => void;
	step: number;
	suffix?: string;
	value: number;
}) {
	const inputId = useId();

	return (
		<div className="space-y-1">
			<label
				className="text-sm font-medium text-muted-foreground"
				htmlFor={inputId}
			>
				{label}
			</label>
			<Input
				disabled={disabled}
				id={inputId}
				max={max}
				min={min}
				onBlur={onCommit}
				onChange={(event) => onChange(Number(event.target.value))}
				onPointerUp={onCommit}
				step={step}
				type="range"
				value={Number.isFinite(value) ? value : 0}
			/>
			<p className="text-xs text-muted-foreground">
				{value.toFixed(2)}
				{suffix ? ` ${suffix}` : ''}
			</p>
		</div>
	);
}
