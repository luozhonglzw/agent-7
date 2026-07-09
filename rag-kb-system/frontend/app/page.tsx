import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <main className="container mx-auto px-4 text-center">
        <h1 className="mb-6 text-5xl font-bold tracking-tight">
          RAG Knowledge Base
        </h1>
        <p className="mb-12 text-xl text-muted-foreground">
          Enterprise-grade AI-powered document search and Q&A system
        </p>

        <div className="flex items-center justify-center gap-4">
          <Link
            href="/auth/login"
            className="rounded-lg bg-primary px-8 py-3 text-lg font-medium text-primary-foreground hover:bg-primary/90"
          >
            Get Started
          </Link>
          <Link
            href="/chat"
            className="rounded-lg border border-border px-8 py-3 text-lg font-medium hover:bg-accent"
          >
            Try Q&A
          </Link>
        </div>

        <div className="mt-20 grid gap-8 md:grid-cols-3">
          <div className="rounded-lg border border-border p-6">
            <h3 className="mb-2 text-lg font-semibold">Document Management</h3>
            <p className="text-muted-foreground">
              Upload PDF, DOCX, PPT, Markdown files. Automatic parsing and
              indexing.
            </p>
          </div>
          <div className="rounded-lg border border-border p-6">
            <h3 className="mb-2 text-lg font-semibold">Smart Search</h3>
            <p className="text-muted-foreground">
              Hybrid search combining dense vectors and BM25 with reranking for
              precise results.
            </p>
          </div>
          <div className="rounded-lg border border-border p-6">
            <h3 className="mb-2 text-lg font-semibold">AI Q&A</h3>
            <p className="text-muted-foreground">
              Ask questions in natural language. Get answers with source
              citations.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
