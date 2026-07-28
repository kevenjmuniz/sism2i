import React from "react";

export function Empty({ text, tone = "loading" }) {
  return (
    <section className={`panel empty ${tone}`} role="status" aria-live="polite">
      {tone === "loading" && <span className="spinner" aria-hidden="true" />}
      {text}
    </section>
  );
}
