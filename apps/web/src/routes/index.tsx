import { createFileRoute, Link } from '@tanstack/react-router'
import Image from 'next/image'
import { Button } from '@/components/ui/button'

export const Route = createFileRoute('/')({
    component: IndexComponent,
})

function IndexComponent() {
    return (
        <div className="grid grid-rows-[20px_1fr_20px] items-center justify-items-center min-h-screen p-8 pb-20 gap-16 sm:p-20 font-[family-name:var(--font-geist-sans)]">
            <main className="flex flex-col gap-8 row-start-2 items-center justify-center w-full">
                <img className="dark:invert" src="/cap_logo-2.svg" alt="AI for EFLT logo" width={180} height={38} />
                {/* Title Below Logo */}
                <h5 className="text-2xl font-bold text-center text-gray-800 dark:text-white">Welcome to AI for EFLT</h5>
                <p className="list-inside list-decimal text-sm text-center sm:text-left font-[family-name:var(--font-geist-mono)]">
                    Leverage the power of machine learning to make data-driven decisions in education.
                </p>

                <Button asChild>
                    <Link to="/select-district">Begin</Link>
                </Button>
            </main>
            <footer className="row-start-3 flex gap-6 flex-wrap items-center justify-center">
                <a
                    className="flex items-center gap-2 hover:underline hover:underline-offset-4"
                    href="https://google.com"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    <img aria-hidden src="/file.svg" alt="File icon" width={16} height={16} />
                    Learn more about this project.
                </a>
            </footer>
        </div>
    )
}
