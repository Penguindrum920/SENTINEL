'use client';

import SectionCard from '@/components/dashboard/SectionCard';
import { PriceSpreadPoint } from '@/types/dashboard';
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Area,
} from 'recharts';

interface PriceSpreadChartProps {
  data: PriceSpreadPoint[];
}

export default function PriceSpreadChart({ data }: PriceSpreadChartProps) {
  return (
    <SectionCard title="Price and Spread" subtitle="Mid-price dynamics with spread regime tracking">
      <div className="h-64 w-full">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 4" stroke="rgba(129, 140, 153, 0.16)" />
            <XAxis
              dataKey="time"
              tick={{ fill: '#8a97a8', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              minTickGap={22}
            />
            <YAxis
              yAxisId="price"
              tick={{ fill: '#8a97a8', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={['auto', 'auto']}
              tickFormatter={(value) => `$${Number(value).toFixed(2)}`}
            />
            <YAxis
              yAxisId="spread"
              orientation="right"
              tick={{ fill: '#8a97a8', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={['auto', 'auto']}
              tickFormatter={(value) => Number(value).toFixed(3)}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#131a24',
                border: '1px solid #273347',
                borderRadius: '10px',
                color: '#dbe3ee',
              }}
              formatter={(value: number, name: string) => {
                if (name === 'price') return [`$${value.toFixed(3)}`, 'Mid Price'];
                return [value.toFixed(4), 'Spread'];
              }}
            />
            <Area
              yAxisId="spread"
              dataKey="spread"
              stroke="#ffcc70"
              fill="#ffcc70"
              fillOpacity={0.12}
              strokeWidth={1.2}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              yAxisId="price"
              dataKey="price"
              stroke="#62d5a4"
              strokeWidth={2.2}
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}
