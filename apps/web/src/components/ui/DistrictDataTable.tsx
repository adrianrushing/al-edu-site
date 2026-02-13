import { useState, useEffect } from 'react'
import Papa from 'papaparse'
import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    getPaginationRowModel,
    getSortedRowModel,
    useReactTable,
} from '@tanstack/react-table'

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import {
    DropdownMenu,
    DropdownMenuCheckboxItem,
    DropdownMenuContent,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronLeft, ChevronRight } from 'lucide-react'

// Type for row data from CSV
interface DistrictRow {
    grade?: string | number
    year?: string | number
    math?: string | number
    rla?: string | number
    leanm?: string
    [key: string]: string | number | undefined
}

// Columns configuration
const selectedColumns: { key: keyof DistrictRow; label: string }[] = [
    { key: 'grade', label: 'Grade' },
    { key: 'year', label: 'Year' },
    { key: 'math', label: 'Math Score' },
    { key: 'rla', label: 'Reading Score' },
]

interface DistrictDataTableProps {
    selectedDistrict: string
}

export default function DistrictDataTable({ selectedDistrict }: DistrictDataTableProps) {
    const [allRows, setAllRows] = useState<DistrictRow[]>([])
    const [filteredRows, setFilteredRows] = useState<DistrictRow[]>([])
    const [searchTerm, setSearchTerm] = useState('')

    // Load CSV and filter by district
    useEffect(() => {
        Papa.parse('/data/AL_Dist.csv', {
            header: true,
            download: true,
            dynamicTyping: true,
            complete: (result) => {
                const rows = result.data as DistrictRow[]
                const districtRows = rows.filter(
                    (row) => (row.leanm ?? '').toLowerCase() === selectedDistrict.toLowerCase()
                )
                setAllRows(districtRows)
                setFilteredRows(districtRows)
            },
        })
    }, [selectedDistrict])

    // Filter rows by search term
    useEffect(() => {
        if (!searchTerm) {
            setFilteredRows(allRows)
        } else {
            const lowerSearch = searchTerm.toLowerCase()
            setFilteredRows(
                allRows.filter((row) =>
                    selectedColumns.some((col) =>
                        String(row[col.key] ?? '').toLowerCase().includes(lowerSearch)
                    )
                )
            )
        }
    }, [searchTerm, allRows])

    // Column definitions for Tanstack Table
    const columns: ColumnDef<DistrictRow>[] = selectedColumns.map((col) => ({
        accessorKey: col.key,
        header: col.label,
    }))

    // Table setup with sorting, pagination
    const table = useReactTable({
        data: filteredRows,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        getSortedRowModel: getSortedRowModel(),
    })

    return (
        <div className="space-y-4">
            <div className="flex items-center justify-between">
                <Input
                    placeholder="Search..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-72"
                />
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="outline">Columns</Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent>
                        {table.getAllColumns().map((column) => (
                            <DropdownMenuCheckboxItem
                                key={column.id}
                                checked={column.getIsVisible()}
                                onCheckedChange={(value) => column.toggleVisibility(value)}
                            >
                                {column.columnDef.header as string}
                            </DropdownMenuCheckboxItem>
                        ))}
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>

            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id}>
                                        {flexRender(header.column.columnDef.header, header.getContext())}
                                    </TableHead>
                                ))}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow key={row.id}>
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id}>
                                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell colSpan={columns.length} className="text-center">
                                    No results found.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>

            {/* Pagination Controls */}
            <div className="flex justify-end space-x-2 pt-4">
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.previousPage()}
                    disabled={!table.getCanPreviousPage()}
                >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                </Button>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={() => table.nextPage()}
                    disabled={!table.getCanNextPage()}
                >
                    Next
                    <ChevronRight className="h-4 w-4" />
                </Button>
            </div>
        </div>
    )
}
