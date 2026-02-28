interface SectionWrapperProps {
  id?: string;
  children: React.ReactNode;
  className?: string;
}

export default function SectionWrapper({
  id,
  children,
  className,
}: SectionWrapperProps) {
  return (
    <section id={id} className={`py-20 md:py-28 px-4 sm:px-6 ${className ?? ""}`}>
      <div className="max-w-5xl mx-auto">{children}</div>
    </section>
  );
}
