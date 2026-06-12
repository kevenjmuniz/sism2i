import React from "react";
import { Search } from "lucide-react";

export function SearchBox({ value, onChange, onSubmit, placeholder }) {
  return (
    <div className="searchbox">
      <Search size={18} />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onSubmit()}
        placeholder={placeholder}
      />
      <button onClick={onSubmit}>Buscar</button>
    </div>
  );
}
