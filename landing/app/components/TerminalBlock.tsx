interface TerminalBlockProps {
  prompt: string;
  output: string;
}

export default function TerminalBlock({ prompt, output }: TerminalBlockProps) {
  return (
    <div className="rounded-xl overflow-hidden border border-subtle bg-[#0d0d0d]">
      {/* Title bar */}
      <div className="flex items-center gap-1.5 px-4 py-3 bg-[#111111] border-b border-subtle">
        <span className="w-3 h-3 rounded-full bg-[#ff5f57]" />
        <span className="w-3 h-3 rounded-full bg-[#febc2e]" />
        <span className="w-3 h-3 rounded-full bg-[#28c840]" />
        <span className="ml-3 text-xs text-secondary font-mono">keepfast</span>
      </div>

      {/* Content */}
      <div className="p-4 sm:p-5 font-mono text-sm leading-relaxed">
        {/* Prompt */}
        <p className="text-accent mb-3">
          <span className="text-secondary">❯ </span>
          {prompt}
        </p>

        {/* Output */}
        <pre className="text-secondary whitespace-pre-wrap text-xs sm:text-sm">
          {output}
        </pre>
      </div>
    </div>
  );
}
