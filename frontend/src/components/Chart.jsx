import React from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { money, number } from "../utils";

const STATUS_COLORS = {
  Ativos: "#16a34a",
  "Em atenção": "#eab308",
  Inativos: "#ea580c",
  Perdidos: "#dc2626",
};

function compactMoney(value) {
  if (Math.abs(value) >= 1000000) return `R$ ${(value / 1000000).toFixed(1)} mi`;
  if (Math.abs(value) >= 1000) return `R$ ${Math.round(value / 1000)} mil`;
  return money(value);
}

function shortLabel(value, length = 22) {
  const label = String(value || "Sem nome");
  return label.length > length ? `${label.slice(0, length - 1)}...` : label;
}

export function Chart({ title, data }) {
  return (
    <section className="panel chartPanel">
      <h2>{title}</h2>
      <div className="chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 18, right: 18, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="#e7edf5" strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="mes" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={compactMoney} width={82} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip formatter={(value) => [money(value), "Faturamento"]} />
            <Line type="monotone" dataKey="total" stroke="#2563eb" strokeWidth={3} dot={false} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function StatusChart({ data }) {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  return (
    <section className="panel chartPanel">
      <h2>Saúde da carteira</h2>
      <div className="chart chartDonut">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={64} outerRadius={92} paddingAngle={2}>
              {data.map((item) => <Cell key={item.name} fill={STATUS_COLORS[item.name]} />)}
            </Pie>
            <Tooltip formatter={(value) => [number(value), "Clientes"]} />
            <Legend verticalAlign="bottom" iconType="circle" iconSize={9} />
            <text x="50%" y="45%" textAnchor="middle" className="donutValue">{number(total)}</text>
            <text x="50%" y="53%" textAnchor="middle" className="donutLabel">clientes</text>
          </PieChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

export function RankingChart({ title, data, nameKey, color }) {
  return (
    <section className="panel chartPanel">
      <h2>{title}</h2>
      <div className="chart chartRanking">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 14, right: 18, left: 8, bottom: 0 }}>
            <CartesianGrid stroke="#e7edf5" strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" tickFormatter={compactMoney} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey={nameKey} tickFormatter={(value) => shortLabel(value)} width={132} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <Tooltip formatter={(value) => [money(value), "Faturamento"]} labelFormatter={(value) => String(value || "Sem nome")} />
            <Bar dataKey="total" fill={color} radius={[0, 4, 4, 0]} maxBarSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
