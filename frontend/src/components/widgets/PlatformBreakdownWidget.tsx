import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'
import { cn, getPlatformColor } from '@/lib/utils'

interface PlatformBreakdownWidgetProps {
  className?: string
}

const mockData = [
  { name: 'Google', value: 35, color: getPlatformColor('google') },
  { name: 'Meta', value: 30, color: getPlatformColor('meta') },
  { name: 'TikTok', value: 20, color: '#000000' },
  { name: 'LinkedIn', value: 10, color: getPlatformColor('linkedin') },
  { name: 'Snapchat', value: 5, color: '#FFFC00' },
]

export function PlatformBreakdownWidget({ className }: PlatformBreakdownWidgetProps) {
  return (
    <div className={cn('h-full p-4', className)}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={mockData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
          >
            {mockData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '8px',
            }}
            formatter={(value: number) => [`${value}%`, 'Share']}
          />
          <Legend
            verticalAlign="bottom"
            height={36}
            formatter={(value) => <span className="text-xs text-foreground">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
