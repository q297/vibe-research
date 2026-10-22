import type { Schemas } from "../api/client";
import { PROVENANCE } from "../api/labels";

const UNVERIFIED = {
  label: "Из введённого текста",
  className: "bg-amber-50 text-amber-800 ring-amber-300",
};

export function ProvenanceBadge({
  provenance,
  unverified = false,
}: {
  provenance: Schemas["Provenance"];
  unverified?: boolean;
}) {
  const { label, className } = unverified ? UNVERIFIED : PROVENANCE[provenance];
  return (
    <span className={`inline-flex shrink-0 rounded-full px-2 py-0.5 text-xs ring-1 ${className}`}>
      {label}
    </span>
  );
}

export function CitationLink({ citation }: { citation: Schemas["Citation"] }) {
  const page = citation.page ? `, стр. ${citation.page}` : "";
  const text = `${citation.title}${page}`;
  if (!citation.url) return <span className="text-slate-500">{text}</span>;
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      className="text-bank underline-offset-2 hover:underline"
    >
      {text}
    </a>
  );
}

export function ClaimView({ claim }: { claim: Schemas["Claim"] }) {
  // A "fact" backed only by user-pasted text is not verified and must not look like one (E4)
  const citations = claim.citations ?? [];
  const unverified =
    claim.provenance === "source_fact" &&
    citations.length > 0 &&
    citations.every((c) => c.kind === "user_input");
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-start gap-2">
        <ProvenanceBadge provenance={claim.provenance} unverified={unverified} />
        <p className="text-sm leading-relaxed">{claim.text}</p>
      </div>
      {claim.citations && claim.citations.length > 0 && (
        <div className="ml-1 flex flex-wrap gap-x-3 text-xs">
          {claim.citations.map((c) => (
            <CitationLink key={`${c.kind}:${c.source_id}`} citation={c} />
          ))}
        </div>
      )}
    </div>
  );
}

export function ProvenanceLegend() {
  return (
    <div className="flex flex-wrap gap-2">
      {(Object.keys(PROVENANCE) as Schemas["Provenance"][]).map((p) => (
        <ProvenanceBadge key={p} provenance={p} />
      ))}
    </div>
  );
}
