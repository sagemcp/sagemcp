import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'

interface AreaChartCardProps {
  data: Array<Record<string, any>>
  dataKey: string
  xKey?: string
  title?: string
  color?: string
  height?: number
}

export function AreaChartCard({
  data,
  dataKey,
  xKey = 'time',
  title,
  color = '#22c55e',
  height = 200,
}: AreaChartCardProps) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-surface-elevated p-4">
      {title && (
        <h3 className="text-sm font-medium text-zinc-300 mb-4">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id={`gradient-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey={xKey}
            stroke="#3f3f46"
            tick={{ fill: '#71717a', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#3f3f46"
            tick={{ fill: '#71717a', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={40}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#27272a',
              border: '1px solid #3f3f46',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#fafafa',
            }}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            fill={`url(#gradient-${dataKey})`}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
